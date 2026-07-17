import json
import os
import shutil
import subprocess
import time
from urllib.parse import urlparse

from deploy.logger import logger


class UpstreamSyncManager:
    """Dispatch the guarded upstream-sync workflow before a client update."""

    ACTIVE_WORKFLOW_STATES = frozenset((
        'queued', 'in_progress', 'pending', 'requested', 'waiting',
    ))

    @staticmethod
    def github_repository_slug(repository):
        """Return ``owner/repository`` for a GitHub HTTPS or SSH URL."""
        repository = str(repository).strip().rstrip('/')
        if repository.startswith('git@github.com:'):
            path = repository.split(':', 1)[1]
        else:
            parsed = urlparse(repository)
            if parsed.netloc.lower() != 'github.com':
                raise ValueError('AutoSyncUpstream requires a github.com repository')
            path = parsed.path.lstrip('/')

        if path.endswith('.git'):
            path = path[:-4]
        parts = path.split('/')
        if len(parts) != 2 or not all(parts):
            raise ValueError('Invalid GitHub repository: {}'.format(repository))
        return '/'.join(parts)

    @staticmethod
    def upstream_sync_needed(upstream_in_development, development_in_stable):
        return not upstream_in_development or not development_in_stable

    @classmethod
    def select_active_workflow_run(cls, runs):
        active = [
            run for run in runs
            if run.get('status') in cls.ACTIVE_WORKFLOW_STATES
        ]
        if not active:
            return None
        return max(active, key=lambda run: int(run.get('databaseId', 0)))

    @staticmethod
    def select_new_workflow_run(runs, known_ids):
        new_runs = [
            run for run in runs
            if int(run.get('databaseId', 0)) not in known_ids
        ]
        if not new_runs:
            return None
        return max(new_runs, key=lambda run: int(run.get('databaseId', 0)))

    @staticmethod
    def select_promotion_pull_request(pull_requests):
        if not pull_requests:
            return None
        return pull_requests[0]

    @property
    def github_cli(self):
        configured = str(getattr(self, 'GitHubCliExecutable', 'gh')).strip()
        if os.path.isabs(configured) and os.path.exists(configured):
            return configured

        executable = shutil.which(configured)
        if executable:
            return executable

        candidates = [
            os.path.join(os.environ.get('ProgramFiles', ''), 'GitHub CLI', 'gh.exe'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'GitHub CLI', 'gh.exe'),
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    def _sync_process(self, args, timeout=60, log_output=True):
        args = [str(arg) for arg in args]
        logger.info('Execute: {}'.format(subprocess.list2cmdline(args)))
        try:
            result = subprocess.run(
                args,
                cwd=self.root_filepath,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout,
                shell=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning('Command timed out after {} seconds'.format(timeout))
            return 124, ''
        except OSError as e:
            logger.warning('{}: {}'.format(type(e).__name__, e))
            return 127, ''

        output = (result.stdout or '').strip()
        if output and log_output:
            logger.info(output)
        return result.returncode, output

    def _sync_git(self, *args, timeout=120, log_output=True):
        return self._sync_process(
            [self.git] + list(args),
            timeout=timeout,
            log_output=log_output,
        )

    def _sync_gh(self, *args, timeout=60, log_output=True):
        return self._sync_process(
            [self.github_cli] + list(args),
            timeout=timeout,
            log_output=log_output,
        )

    def _ensure_upstream_remote(self):
        code, _ = self._sync_git('remote', 'get-url', 'upstream', log_output=False)
        if code == 0:
            command = ('remote', 'set-url', 'upstream', self.UpstreamRepository)
        else:
            command = ('remote', 'add', 'upstream', self.UpstreamRepository)
        code, _ = self._sync_git(*command)
        return code == 0

    def _fetch_sync_refs(self):
        if not self._ensure_upstream_remote():
            return False

        upstream_refspec = '+refs/heads/{0}:refs/remotes/upstream/{0}'.format(
            self.UpstreamBranch
        )
        code, _ = self._sync_git(
            'fetch', '--no-tags', 'upstream', upstream_refspec, timeout=180
        )
        if code != 0:
            return False

        return self._fetch_origin_refs()

    def _fetch_origin_refs(self):
        development_refspec = '+refs/heads/{0}:refs/remotes/origin/{0}'.format(
            self.DevelopmentBranch
        )
        stable_refspec = '+refs/heads/{0}:refs/remotes/origin/{0}'.format(
            self.Branch
        )
        code, _ = self._sync_git(
            'fetch', '--no-tags', 'origin', development_refspec, stable_refspec,
            timeout=180,
        )
        return code == 0

    def _is_ancestor(self, ancestor, descendant):
        code, _ = self._sync_git(
            'merge-base', '--is-ancestor', ancestor, descendant,
            log_output=False,
        )
        if code in (0, 1):
            return code == 0
        raise RuntimeError('Unable to compare Git revisions')

    def _workflow_runs(self, repository):
        code, output = self._sync_gh(
            'run', 'list',
            '--repo', repository,
            '--workflow', self.SyncWorkflow,
            '--branch', self.Branch,
            '--event', 'workflow_dispatch',
            '--limit', '10',
            '--json', 'databaseId,status,conclusion,url,createdAt',
            log_output=False,
        )
        if code != 0:
            raise RuntimeError('Unable to list upstream-sync workflow runs')
        return json.loads(output or '[]')

    def _dispatch_workflow(self, repository):
        runs = self._workflow_runs(repository)
        active = self.select_active_workflow_run(runs)
        if active:
            logger.info('Reuse active upstream-sync workflow run')
            return int(active['databaseId'])

        known_ids = {int(run.get('databaseId', 0)) for run in runs}
        code, _ = self._sync_gh(
            'workflow', 'run', self.SyncWorkflow,
            '--repo', repository,
            '--ref', self.Branch,
        )
        if code != 0:
            raise RuntimeError('Unable to dispatch upstream-sync workflow')

        deadline = time.time() + 45
        while time.time() < deadline:
            time.sleep(3)
            run = self.select_new_workflow_run(
                self._workflow_runs(repository), known_ids
            )
            if run:
                return int(run['databaseId'])
        raise RuntimeError('Timed out while locating the upstream-sync workflow run')

    def _wait_workflow(self, repository, run_id):
        deadline = time.time() + int(self.SyncTimeout)
        previous = None
        while time.time() < deadline:
            code, output = self._sync_gh(
                'run', 'view', str(run_id),
                '--repo', repository,
                '--json', 'status,conclusion,url',
                log_output=False,
            )
            if code != 0:
                raise RuntimeError('Unable to read upstream-sync workflow status')
            data = json.loads(output)
            status = data.get('status')
            if status != previous:
                logger.info('Upstream-sync workflow: {} {}'.format(
                    status, data.get('url', '')
                ))
                previous = status
            if status == 'completed':
                conclusion = data.get('conclusion')
                if conclusion == 'success':
                    logger.info('Official upstream sync completed successfully')
                    return True
                logger.warning('Official upstream sync finished with {}'.format(conclusion))
                return False
            time.sleep(5)

        logger.warning('Official upstream sync exceeded the configured timeout')
        return False

    def _promotion_pull_request(self, repository):
        code, output = self._sync_gh(
            'pr', 'list',
            '--repo', repository,
            '--base', self.Branch,
            '--head', self.DevelopmentBranch,
            '--state', 'open',
            '--json', 'url,number,isDraft',
            log_output=False,
        )
        if code != 0:
            raise RuntimeError('Unable to list stable promotion pull requests')

        pull_request = self.select_promotion_pull_request(json.loads(output or '[]'))
        if pull_request:
            return pull_request

        title = 'chore: promote tested {}'.format(self.DevelopmentBranch)
        body = (
            'The official upstream sync workflow completed successfully. '
            'All guarded resolution and updater tests passed, and the rollback '
            'branch points to the previous stable revision.'
        )
        code, output = self._sync_gh(
            'pr', 'create',
            '--repo', repository,
            '--base', self.Branch,
            '--head', self.DevelopmentBranch,
            '--title', title,
            '--body', body,
        )
        if code != 0:
            raise RuntimeError('Unable to create stable promotion pull request')
        return {'url': output.splitlines()[-1].strip(), 'isDraft': False}

    def _promote_stable(self, repository):
        if not self._fetch_origin_refs():
            raise RuntimeError('Unable to refresh branches before stable promotion')

        development_ref = 'refs/remotes/origin/{}'.format(self.DevelopmentBranch)
        stable_ref = 'refs/remotes/origin/{}'.format(self.Branch)
        if self._is_ancestor(development_ref, stable_ref):
            logger.info('Tested development branch is already in stable')
            return True

        pull_request = self._promotion_pull_request(repository)
        pull_request_url = pull_request['url']
        if pull_request.get('isDraft'):
            code, _ = self._sync_gh('pr', 'ready', pull_request_url, '--repo', repository)
            if code != 0:
                raise RuntimeError('Unable to mark stable promotion pull request ready')

        code, _ = self._sync_gh(
            'pr', 'merge', pull_request_url,
            '--repo', repository,
            '--merge',
            timeout=180,
        )
        if code != 0:
            if self._fetch_origin_refs() and self._is_ancestor(
                    development_ref, stable_ref):
                return True
            raise RuntimeError('Unable to merge stable promotion pull request')

        deadline = time.time() + 60
        while time.time() < deadline:
            if self._fetch_origin_refs() and self._is_ancestor(
                    development_ref, stable_ref):
                logger.info('Tested development branch promoted to stable')
                return True
            time.sleep(3)
        raise RuntimeError('Stable branch did not contain the tested development revision')

    def _complete_sync(self, repository, run_id):
        if not self._wait_workflow(repository, run_id):
            return False
        return self._promote_stable(repository)

    def _sync_upstream_at_startup(self):
        if not self._fetch_sync_refs():
            logger.warning('Unable to fetch branches for official upstream check')
            return False

        upstream_ref = 'refs/remotes/upstream/{}'.format(self.UpstreamBranch)
        development_ref = 'refs/remotes/origin/{}'.format(self.DevelopmentBranch)
        stable_ref = 'refs/remotes/origin/{}'.format(self.Branch)
        upstream_in_development = self._is_ancestor(upstream_ref, development_ref)
        development_in_stable = self._is_ancestor(development_ref, stable_ref)
        if not self.upstream_sync_needed(
                upstream_in_development, development_in_stable):
            logger.info('Official upstream and stable branch are already synchronized')
            return False

        if not self.github_cli:
            logger.warning('GitHub CLI is not installed; keep using the current stable branch')
            return False
        code, _ = self._sync_gh('auth', 'status', '--hostname', 'github.com')
        if code != 0:
            logger.warning('GitHub CLI is not authenticated; keep using the current stable branch')
            return False

        repository = self.github_repository_slug(self.Repository)
        run_id = self._dispatch_workflow(repository)
        return self._complete_sync(repository, run_id)

    def sync_upstream_at_startup(self):
        if not getattr(self, 'AutoSyncUpstream', False):
            return False

        logger.hr('Sync official upstream', 0)
        try:
            if not os.path.isdir(os.path.join(self.root_filepath, '.git')):
                logger.info('Git repository is not initialized; skip upstream sync')
                return False
            return self._sync_upstream_at_startup()
        except Exception as e:
            logger.warning('Official upstream sync skipped: {}: {}'.format(
                type(e).__name__, e
            ))
            logger.warning('Continue with the last verified stable branch')
            return False
