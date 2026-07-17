import os
import unittest

from deploy.upstream import UpstreamSyncManager


class FailingSync(UpstreamSyncManager):
    AutoSyncUpstream = True
    root_filepath = os.getcwd()

    def _sync_upstream_at_startup(self):
        raise RuntimeError('simulated failure')


class CompletingSync(UpstreamSyncManager):
    def __init__(self, workflow_success):
        self.workflow_success = workflow_success
        self.promotions = 0

    def _wait_workflow(self, repository, run_id):
        return self.workflow_success

    def _promote_stable(self, repository):
        self.promotions += 1
        return True


class TestUpstreamSyncManager(unittest.TestCase):
    def test_parse_https_repository(self):
        self.assertEqual(
            UpstreamSyncManager.github_repository_slug(
                'https://github.com/fuyiyi1982/AzurLaneAutoScript.git'
            ),
            'fuyiyi1982/AzurLaneAutoScript',
        )

    def test_parse_ssh_repository(self):
        self.assertEqual(
            UpstreamSyncManager.github_repository_slug(
                'git@github.com:fuyiyi1982/AzurLaneAutoScript.git'
            ),
            'fuyiyi1982/AzurLaneAutoScript',
        )

    def test_reject_non_github_repository(self):
        with self.assertRaises(ValueError):
            UpstreamSyncManager.github_repository_slug('https://example.com/owner/repo')

    def test_no_sync_when_both_relationships_are_current(self):
        self.assertFalse(UpstreamSyncManager.upstream_sync_needed(True, True))

    def test_sync_when_upstream_or_stable_is_behind(self):
        self.assertTrue(UpstreamSyncManager.upstream_sync_needed(False, True))
        self.assertTrue(UpstreamSyncManager.upstream_sync_needed(True, False))

    def test_select_active_and_new_workflow_runs(self):
        runs = [
            {'databaseId': 10, 'status': 'completed'},
            {'databaseId': 11, 'status': 'queued'},
            {'databaseId': 12, 'status': 'in_progress'},
        ]
        self.assertEqual(
            UpstreamSyncManager.select_active_workflow_run(runs)['databaseId'],
            12,
        )
        self.assertEqual(
            UpstreamSyncManager.select_new_workflow_run(runs, {10, 11})['databaseId'],
            12,
        )

    def test_select_existing_promotion_pull_request(self):
        pull_request = {'number': 2, 'url': 'https://github.com/example/repo/pull/2'}

        self.assertIs(
            UpstreamSyncManager.select_promotion_pull_request([pull_request]),
            pull_request,
        )
        self.assertIsNone(UpstreamSyncManager.select_promotion_pull_request([]))

    def test_successful_workflow_promotes_stable(self):
        sync = CompletingSync(workflow_success=True)

        self.assertTrue(sync._complete_sync('example/repo', 1))
        self.assertEqual(sync.promotions, 1)

    def test_failed_workflow_does_not_promote_stable(self):
        sync = CompletingSync(workflow_success=False)

        self.assertFalse(sync._complete_sync('example/repo', 1))
        self.assertEqual(sync.promotions, 0)

    def test_failure_keeps_the_last_stable_version(self):
        self.assertFalse(FailingSync().sync_upstream_at_startup())


if __name__ == '__main__':
    unittest.main()
