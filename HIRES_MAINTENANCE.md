# 2560×1440 与上游自动同步维护手册

> 最后核对日期：2026-07-17
>
> 适用仓库：fuyiyi1982/AzurLaneAutoScript
>
> 用途：记录本仓库相对官方项目的定制、自动更新架构、验证方法和故障处理流程，供后续调试与继续开发使用。

## 1. 快速事实

| 项目 | 当前约定 |
| --- | --- |
| 官方仓库 | https://github.com/LmeSzinc/AzurLaneAutoScript |
| 个人仓库 | https://github.com/fuyiyi1982/AzurLaneAutoScript |
| 官方来源分支 | upstream/master |
| 开发分支 | hires-dev |
| 客户端稳定分支 | hires-stable |
| 滚动回退分支 | hires-stable-rollback |
| GitHub 默认分支 | hires-stable |
| 客户端本地配置 | config/deploy.yaml，该文件被 Git 忽略 |
| 自动同步工作流 | .github/workflows/upstream-sync.yml |
| 客户端同步实现 | deploy/upstream.py |

本仓库的两项核心定制是：

1. 保留 Alas 原有的 1280×720 识别坐标系，同时支持在 2560×1440 的模拟器画面上运行。
2. 客户端启动时检测官方更新；只有合并和测试成功后，才允许更新 hires-dev、创建合并请求并晋级 hires-stable。

## 2. 设计目标与安全边界

- 支持的设备分辨率目前只有 1280×720 和 2560×1440。
- 图像识别、模板和业务逻辑继续使用 1280×720，不批量放大现有素材。
- 2560×1440 截图在进入识别逻辑前缩小为 1280×720。
- 点击和滑动坐标根据控制后端所使用的坐标空间自动换算。
- 官方代码不会直接合并进 hires-stable。
- 合并冲突、测试失败、网络失败、GitHub 登录失效、超时或合并请求失败时，客户端继续使用最后一个已验证的 hires-stable。
- 服务端不会主动把代码推入正在运行的客户端。实际机制是客户端启动时发起检查，等待稳定分支晋级，然后由原更新器拉取 hires-stable。

## 3. 2560×1440 适配原理

### 3.1 坐标模型

适配层把 1280×720 作为固定的“虚拟画布”：

    2560×1440 原始截图
            ↓ 缩小 2 倍
    1280×720 虚拟画布
            ↓
    原有图像识别、按钮区域和业务逻辑
            ↓
    根据控制后端换算点击、滑动和矩形坐标

这样可以最大程度保留官方项目现有的图片资源、区域坐标和识别算法，降低以后同步官方更新时的维护量。

### 3.2 控制后端坐标

- minitouch、MaaTouch 和 scrcpy 已经使用 Alas 的虚拟坐标，因此普通控制指令不再二次放大。
- ADB 等使用设备原生坐标的后端，在 2560×1440 下把坐标和向量放大 2 倍。
- 如果坐标来自设备原生层级信息，传给虚拟坐标后端前会反向缩小。
- 横竖屏检测会先规范为横屏尺寸，因此 1440×2560 也能识别为受支持的 2560×1440 设备。
- MuMu 12 的 DroidCast_raw 会自行把竖向 framebuffer 转成横向截图；通用截图层遇到已是受支持的横屏尺寸时必须直接保留，不能再按设备方向旋转一次。

### 3.3 相关文件

| 文件 | 作用 |
| --- | --- |
| module/device/resolution.py | 分辨率识别、截图归一化、坐标和向量换算 |
| module/device/device.py | 将 ResolutionAdapter 接入 Device |
| module/device/screenshot.py | 截图进入识别前统一归一化，并更新不支持分辨率提示 |
| module/device/control.py | 点击、长按、滑动等控制入口使用坐标适配 |
| module/device/method/uiautomator_2.py | 启动时读取和校验设备原生分辨率 |
| module/device/method/droidcast.py | DroidCast 使用真实 framebuffer 尺寸 |
| module/os/globe_operation.py | 大世界海域标题识别入口 |
| module/os/zone_detection.py | 对 2560×1440 缩图后的隐蔽海域标题做局部容错识别 |
| module/os_handler/map_order.py | G.M. 指令页进入、执行与退出流程 |
| module/os/order_detection.py | 兼容新旧 G.M. 指令页的轻量识别策略 |
| tests/test_resolution_adapter.py | 分辨率、截图和控制坐标的 10 项回归测试 |
| tests/test_os_globe_high_resolution.py | 隐蔽海域高分辨率缩图识别回归测试 |
| tests/test_os_order_detection.py | 新旧 G.M. 指令页及误识别保护的 3 项回归测试 |
| tests/fixtures/zone_obscure_2560x1440_downsampled.png | 从真实故障截图提取的最小识别区域，不含账号信息 |
| tests/fixtures/order_gms_2560x1440_downsampled.png | 从真实故障截图提取的 G.M. 指令页最小识别区域 |

### 3.4 运行时预期日志

在 2560×1440 设备上应能看到类似信息：

    Native resolution: 2560x1440
    Use 1280x720 virtual resolution for image recognition and controls

如果日志仍显示“不支持分辨率”，先确认模拟器报告的是精确的 2560×1440，而不是 2550×1440、2560×1600 或经过系统缩放后的其他尺寸。

## 4. 自动同步与稳定晋级流程

### 4.1 启动入口

deploy/git.py 中的 GitManager.git_install 会先调用 sync_upstream_at_startup，然后再执行原有的稳定分支更新逻辑。

客户端首先拉取并比较：

    upstream/master 是否已经包含在 origin/hires-dev
    origin/hires-dev 是否已经包含在 origin/hires-stable

两项都成立时说明无需处理，启动检查会直接结束，不触发 GitHub Actions。

### 4.2 发现更新后的完整顺序

1. 客户端确认 GitHub CLI 已安装且已登录。
2. 客户端在 hires-stable 上手动触发 upstream-sync.yml。
3. 工作流检出 hires-dev，并在临时工作区合并 upstream/master。
4. 如果发生合并冲突，工作流立即失败，不推送任何新代码。
5. 工作流使用 Python 3.10 安装 requirements-ci.txt。
6. 工作流运行分辨率测试、更新器测试和关键文件语法编译。
7. 全部通过后才把合并结果推送到 hires-dev。
8. 工作流把晋级前的 hires-stable 保存到 hires-stable-rollback。
9. 客户端复用或创建 hires-dev → hires-stable 合并请求，并使用已登录用户权限合并。
10. 客户端再次拉取分支，确认 hires-dev 确实已经包含在 hires-stable。
11. 原有更新器继续从 hires-stable 更新本地客户端。

工作流使用固定并发组 hires-official-upstream-sync，同一时间只允许一个同步任务运行。重复启动时，客户端会优先复用仍在排队或执行中的任务。

### 4.3 为什么合并请求由客户端创建

最初曾尝试让 GitHub Actions 自己创建合并请求，但仓库的 Actions 令牌返回：

    Resource not accessible by integration

因此最终架构是：

- GitHub Actions 负责合并官方代码、测试、推送 hires-dev 和保存回退点。
- 已登录的客户端 GitHub CLI 负责创建或复用合并请求，并合并到 hires-stable。

后续调试时不要误以为工作流本身应该创建合并请求。除非重新设计 GitHub App、PAT 或仓库权限，否则应保留当前职责划分。

### 4.4 失败保护

以下情况都不会改动 hires-stable：

- 无法访问官方仓库或个人仓库。
- 官方代码与 hires-dev 发生合并冲突。
- Python 依赖安装失败。
- 任一单元测试或语法检查失败。
- 工作流超时或结论不是 success。
- GitHub CLI 未安装或登录失效。
- 合并请求无法创建、无法设为 ready 或无法合并。
- 合并后无法验证 hires-dev 已进入 hires-stable。

deploy/upstream.py 会捕获异常、写入警告日志，并继续使用最后一个已验证的稳定分支。

## 5. 客户端配置

本机实际使用的 config/deploy.yaml 应包含以下核心配置：

    Deploy:
      Git:
        Repository: https://github.com/fuyiyi1982/AzurLaneAutoScript
        Branch: hires-stable
        AutoUpdate: true
        AutoSyncUpstream: true
        UpstreamRepository: https://github.com/LmeSzinc/AzurLaneAutoScript
        UpstreamBranch: master
        DevelopmentBranch: hires-dev
        SyncWorkflow: upstream-sync.yml
        SyncTimeout: 900
        GitHubCliExecutable: gh

注意：

- config/deploy.yaml 被 .gitignore 忽略，属于每台客户端的本地配置，不会随仓库推送。
- deploy/template 中提供了相同字段，但 AutoSyncUpstream 默认是 false，避免官方用户或新安装误触发个人仓库流程。
- SyncTimeout 为秒。发现更新时，客户端最多等待 900 秒；没有更新时不会等待工作流。
- 代码会从 PATH、Program Files 和 LocalAppData 的常见位置寻找 gh.exe。
- 不要在仓库、文档、日志或提交中保存 GitHub 访问令牌。

检查登录状态：

    gh auth status --hostname github.com

登录失效时重新执行：

    gh auth login

## 6. Git 分支和远程仓库规则

预期远程配置：

    origin    https://github.com/fuyiyi1982/AzurLaneAutoScript
    upstream  https://github.com/LmeSzinc/AzurLaneAutoScript

本机已把 upstream 的推送地址设置为 no_push，目的是避免误推官方仓库。可以用以下命令检查：

    git remote -v
    git config --get-all remote.upstream.pushurl

分支职责：

| 分支 | 职责 |
| --- | --- |
| master | 官方基线的本地跟踪历史，不作为客户端更新目标 |
| hires-dev | 接收自定义开发和经过测试的官方合并 |
| hires-stable | 客户端唯一稳定更新源，也是 GitHub 默认分支 |
| hires-stable-rollback | 每次受保护同步前记录上一个稳定提交，只保留一个滚动回退点 |

维护规则：

- 不要直接在 hires-stable 上开发。
- 自定义修改先进入 hires-dev。
- 测试通过后通过合并请求进入 hires-stable。
- 客户端配置始终指向 hires-stable。
- 官方更新始终由 upstream/master 合并进 hires-dev，不要把个人仓库 master 当作自动更新源。

## 7. 测试与验证

### 7.1 本地自动测试

本机应使用 config/deploy.yaml 中 PythonExecutable 指向的项目 Python。当前 Windows 安装对应 .\toolkit\python.exe；不要默认使用 PATH 中的系统 Python，因为它可能没有 Alas 的 NumPy、OpenCV 和 PyWebIO 依赖。GitHub Actions 中则使用 setup-python 创建的 python。

安装精简 CI 依赖：

    .\toolkit\python.exe -m pip install --disable-pip-version-check -r requirements-ci.txt

运行分辨率测试：

    .\toolkit\python.exe -m unittest discover -s tests -p test_resolution_adapter.py -v

运行高分辨率大世界识别测试：

    .\toolkit\python.exe -m unittest discover -s tests -p test_os_globe_high_resolution.py -v

运行 G.M. 指令页识别测试：

    .\toolkit\python.exe -m unittest discover -s tests -p test_os_order_detection.py -v

运行更新器测试：

    .\toolkit\python.exe -m unittest discover -s tests -p test_upstream_sync.py -v

当前预期是分辨率 10 项、高分辨率大世界识别 2 项、G.M. 指令页识别 3 项、更新器 10 项，共 25 项通过。

运行关键文件语法检查：

    .\toolkit\python.exe -m py_compile deploy/upstream.py deploy/git.py deploy/config.py module/os/globe_operation.py module/os/zone_detection.py module/os/order_detection.py module/os_handler/map_order.py module/device/resolution.py module/device/device.py module/device/screenshot.py module/device/control.py module/device/method/uiautomator_2.py module/device/method/droidcast.py

### 7.2 2560×1440 模拟器冒烟测试

单元测试通过后，涉及设备或控制代码的改动还应在真实模拟器上检查：

1. 模拟器和游戏都设置为 2560×1440 横屏。
2. 启动客户端，确认日志记录 Native resolution: 2560x1440。
3. 确认截图识别正常，没有整体偏移、裁切或黑边。
4. 分别验证常用点击、长按和滑动。
5. 如果使用 DroidCast、ADB、MaaTouch 或 scrcpy，至少验证实际启用的后端。
6. 再用 1280×720 运行一次，确认原分辨率没有回归。

CI 不能连接模拟器，因此真实设备冒烟测试仍然是必要的。

### 7.3 手动触发线上流程

    gh workflow run upstream-sync.yml --repo fuyiyi1982/AzurLaneAutoScript --ref hires-stable
    gh run list --repo fuyiyi1982/AzurLaneAutoScript --workflow upstream-sync.yml --limit 10

如果本次修改包含 `upstream-sync.yml` 本身或新增测试，首次远端验证应把 `--ref` 改为 `hires-dev`，确保 GitHub Actions 使用开发分支里的新版工作流。晋级稳定分支后，再用 `--ref hires-stable` 做一次幂等复验。

查看失败日志：

    gh run view RUN_ID --repo fuyiyi1982/AzurLaneAutoScript --log-failed

如果官方、开发和稳定分支已经同步，线上任务应成功结束，并跳过依赖安装、测试、推送和回退点更新。这是预期的幂等行为。

## 8. 日常开发操作

### 8.1 开始修改前

    git status --short --branch
    git fetch origin
    git fetch upstream master
    git switch hires-dev
    git pull --ff-only origin hires-dev

先确认工作区里的未跟踪文件属于谁。不要为了获得“干净工作区”而删除不认识的文件。

### 8.2 修改完成后

1. 运行第 7 节的本地测试。
2. 提交到 hires-dev 并推送。
3. 触发 upstream-sync.yml，让远端再次验证并保存回退点。
4. 只有工作流成功后才创建 hires-dev → hires-stable 合并请求。
5. 合并后确认 hires-dev 是 hires-stable 的祖先：

       git fetch origin hires-dev hires-stable
       git merge-base --is-ancestor origin/hires-dev origin/hires-stable

   退出码为 0 才表示晋级完成。

### 8.3 新增测试时

除了新增 tests 下的测试文件，还要检查 .github/workflows/upstream-sync.yml 是否会实际运行它。当前工作流只显式运行：

- test_resolution_adapter.py
- test_os_globe_high_resolution.py
- test_os_order_detection.py
- test_upstream_sync.py
- 一组关键 Python 文件的 py_compile

若以后把高分辨率适配扩展到新模块，应同时扩大工作流的测试和语法检查范围。

## 9. 故障排查

### 9.1 客户端启动后没有检测更新

依次检查：

1. config/deploy.yaml 中 AutoSyncUpstream 是否为 true。
2. Repository 是否指向个人仓库，Branch 是否为 hires-stable。
3. gh auth status 是否成功。
4. git remote -v 中 origin 和 upstream 是否正确。
5. 手动执行 git fetch upstream master 和 git fetch origin hires-dev hires-stable。
6. 比较分支关系：

       git merge-base --is-ancestor upstream/master origin/hires-dev
       git merge-base --is-ancestor origin/hires-dev origin/hires-stable

   两条都返回 0 时，本来就不需要同步。

### 9.2 工作流在合并步骤失败

通常表示官方代码修改了本仓库同一区域。不要直接在 hires-stable 上解决冲突。建议：

1. 从 origin/hires-dev 建立临时调试分支。
2. 在临时分支合并 upstream/master。
3. 重点检查第 3.3 节列出的分辨率相关文件，以及 deploy 目录的同步实现。
4. 解决冲突后运行全部 25 项测试和模拟器冒烟测试。
5. 再把修复提交到 hires-dev，重新触发工作流。

### 9.3 工作流测试失败

- 使用 gh run view RUN_ID --log-failed 获取准确失败步骤。
- 先在本机用 requirements-ci.txt 的依赖环境复现。
- 如果是官方新增依赖，只把测试真正需要的最小依赖加入 requirements-ci.txt。
- 如果官方改变了设备、截图或控制接口，优先调整 ResolutionAdapter 的接入点，不要批量修改业务坐标。
- 测试没有全部通过前，不要手动绕过流程合并稳定分支。

### 9.4 工作流成功但没有合并请求

这是客户端晋级阶段的问题，检查：

    gh auth status --hostname github.com
    gh pr list --repo fuyiyi1982/AzurLaneAutoScript --base hires-stable --head hires-dev --state all

确认登录用户对个人仓库有写权限，并且令牌具备 repo 和 workflow 所需权限。客户端会优先复用已有的打开状态合并请求。

### 9.5 2560×1440 能截图但点击偏移

1. 从日志确认识别到的原生分辨率。
2. 确认实际控制后端名称。
3. 检查该后端是否应该加入 ResolutionAdapter.VIRTUAL_CONTROL_METHODS。
4. 区分坐标来自 Alas 虚拟画布，还是来自设备原生层级信息。
5. 为问题后端补充坐标单元测试，再做真实模拟器验证。

最常见错误是对已经使用虚拟坐标的后端再次放大，或者把设备原生坐标未经缩小传给虚拟后端。

### 9.6 DroidCast_raw 报 1440×2560 不受支持

如果模拟器明确设置为 2560×1440，但日志依次出现 DroidCast_raw、Screen_size: 1440x2560 和 Resolution not supported，说明横屏截图被重复旋转成了竖屏。

2026-07-17 的修复让通用截图层直接保留已经是 2560×1440 的横屏画面，同时继续把真正的 1440×2560 竖屏画面旋转一次。对应回归测试是：

- test_mumu_landscape_screenshot_is_not_rotated_twice
- test_portrait_high_resolution_screenshot_is_rotated_once

排查同类问题时，应同时确认设备方向、DroidCast framebuffer 尺寸、DroidCast_raw 返回尺寸和通用截图处理后的尺寸，避免只交换宽高数字而没有真正旋转像素。

### 9.7 隐蔽海域结算后停在海域详情页

典型日志是已经点击 `TEMPLATE_STORAGE_OBSCURE` 和 `STORAGE_COORDINATE_CHECKOUT`，游戏也正确进入“卡利比安海A-隐秘海域”等海域详情页，但约 60 秒后仍报 `GameStuckError: Wait too long`。

2026-07-17 的真实故障截图证明坐标换算和点击都正确。问题发生在识别阶段：2560×1440 截图缩小到 1280×720 后，标题文字的抗锯齿发生变化，`ZONE_OBSCURE` 相似度约为 0.8146，低于原来的 0.85 门槛。

修复只作用于 `ZONE_OBSCURE`：

- 模板相似度门槛改为 0.80。
- 同时要求标题颜色在阈值 10 内匹配，避免仅靠放宽模板造成误识别。
- 其他五种海域、全局模板门槛和点击坐标保持不变。
- 回归测试使用从真实故障截图提取的最小区域，明确验证旧门槛失败、修复路径成功。

排查同类问题时，先保存错误截图并离线计算目标模板相似度和颜色差异。不要在没有证据时修改坐标，也不要降低全局识别门槛。

### 9.8 进入 G.M. 指令页后一直显示“正在扫描”

典型日志是 `ORDER_SCAN`、`Order enter`、点击 `ORDER_ENTER` 后再无进展，约 60 秒后在 `order_enter()` 报 `GameStuckError`，等待集合中包含 `ORDER_CHECK`。画面已经进入 G.M. 指令页，中央显示“正在扫描”，但日志里还没有点击 `ORDER_SCAN`。

这里的“正在扫描”是指令页背景状态，不代表程序已经执行了空域侦察。2026-07-17 的真实故障截图显示，程序原来的 `ORDER_CHECK` 依赖左下角蓝色“i”图标，而当前游戏界面已把该位置换成角色头像，旧模板相似度只有约 0.4612。因此程序一直误以为尚未进入指令页。

修复采用双重兼容识别：

- 优先保留旧版左下角“i”图标模板，兼容旧界面。
- 旧模板失败时，检测左上角稳定的黄色 G.M. 退出图标。
- 不修改 `ORDER_ENTER`、`ORDER_SCAN` 或退出按钮的点击坐标。
- 回归测试验证新版页面可识别、旧版页面仍可识别、无关页面不会误识别。

遇到相同症状时，先看调用栈是否停在 `order_enter()`。如果已经进入 `order_execute()`，则属于后续指令按钮或弹窗问题，不应继续调整本节的页面检查条件。

### 9.9 临时停止自动同步

只停止官方同步，但仍允许客户端拉取现有稳定版：

    AutoSyncUpstream: false
    AutoUpdate: true

完全冻结客户端代码版本：

    AutoSyncUpstream: false
    AutoUpdate: false

恢复前应先人工确认 hires-stable 状态。

## 10. 回退方案

正常情况下，失败代码不会进入 hires-stable，因此无需回退。如果错误通过了测试并已合并，优先使用“新提交撤销”的方式保留历史：

    git fetch origin
    git switch -c codex/revert-bad-stable origin/hires-stable
    git revert -m 1 BAD_MERGE_SHA

然后运行全部测试，推送该修复分支并创建合并请求到 hires-stable。

紧急情况下可以把 hires-stable-rollback 强制恢复为稳定分支，但这会改写远端分支历史：

    git fetch origin
    git push --force-with-lease origin origin/hires-stable-rollback:hires-stable

除非已经确认回退点、没有其他并行修改，并且用户明确同意，否则不要执行紧急强制回退。回退后还要让本地客户端重新拉取稳定分支。

## 11. 已知限制

- 只支持精确的 1280×720 和 2560×1440；不是任意分辨率自适应方案。
- 只处理横屏 16:9 画面，没有针对超宽屏、平板比例或系统黑边做通用布局适配。
- CI 是单元测试和语法检查，不能替代模拟器端到端测试。
- 自动晋级依赖客户端上的 GitHub CLI 登录状态。
- 发现更新时，客户端启动可能等待远端工作流，最长时间由 SyncTimeout 控制。
- hires-stable-rollback 只有一个滚动回退点，不是完整发布归档。
- 如果仓库以后启用强制评审、必需检查或其他分支保护，客户端自动合并可能被阻止；此时稳定分支仍保持不变，但需要人工完成评审。
- 如果官方以后原生支持 2560×1440，应重新评估是否删除本适配层，避免两套缩放逻辑叠加。

## 12. 初次上线与验证记录

以下提交号和链接是初次实现时的历史证据，不代表永远的最新版本：

| 内容 | 记录 |
| --- | --- |
| 官方基线 | a97e76ca |
| 2560×1440 适配 | 0b64b72f |
| 自动同步初版 | f97edfbd |
| CI 补充 pywebio | e2df25dd |
| 客户端负责稳定晋级 | fdbea6c5 |
| 首次完整稳定合并 | 98dcbfd5 |
| 首次完整线上同步 | https://github.com/fuyiyi1982/AzurLaneAutoScript/actions/runs/29564358583 |
| 首次稳定晋级合并请求 | https://github.com/fuyiyi1982/AzurLaneAutoScript/pull/2 |
| 首次“无更新直接跳过”演练 | https://github.com/fuyiyi1982/AzurLaneAutoScript/actions/runs/29564519908 |

查询最新状态时应以远端分支为准：

    git fetch origin
    git log -1 --oneline origin/hires-stable
    git log -1 --oneline origin/hires-dev
    git log -1 --oneline origin/hires-stable-rollback

## 13. 本机文件保护

编写本文档时，本机存在以下未跟踪的用户文件：

- deploy/Termux/
- deploy/launcher/Alas-gui.bat

它们不属于本次高分辨率或自动同步提交。后续调试、切换分支、清理工作区或处理冲突时，不要删除、覆盖或提交这些文件，除非用户明确要求。

## 14. 后续会话接手清单

新的维护者或 Codex 会话开始工作前：

1. 先完整阅读本文档。
2. 执行 git status --short --branch，识别并保护用户自己的修改和未跟踪文件。
3. 执行 git remote -v，确认 origin 是个人仓库、upstream 是官方仓库且不可推送。
4. 拉取 origin 和 upstream，但不要直接修改 hires-stable。
5. 复现问题并收集客户端日志、GitHub Actions 运行链接、模拟器分辨率和实际控制后端。
6. 在 hires-dev 或临时调试分支修复。
7. 运行 25 项自动测试、py_compile 和必要的模拟器冒烟测试。
8. 通过远端工作流和合并请求晋级 hires-stable。
9. 最后验证分支祖先关系、默认分支、回退点和客户端本地配置。

如果实现发生变化，应在同一个提交或同一个合并请求中同步更新本文档，避免维护手册落后于代码。
