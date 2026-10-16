# Shotgun Motion Lab / 霰弹枪动作实验室

一个适合手机和桌面浏览器的互动教育网页。外观、剖面与对照视图共用同一套演示状态；通过按钮、手机动作和慢速播放，观察非品牌化模型的部件关系。木纹、金属明暗、窗口遮挡和短促反馈用于加强视觉表现，剖面与运动仍是教学抽象，不对应具体实物构造。

## 在线演示

GitHub Pages：<https://lsdlyu.github.io/shotgun-motion-lab/>

## 使用方法

1. **互动体验**：模型下方的按钮始终可用。按顺序轻拉、轻推，再点按“反馈演示”。动画进行中锁定后续输入，反馈结束后可开始下一轮。
2. **外观 / 剖面 / 对照**：随时切换，保留当前阶段。剖面可进一步放大查看机匣内部；对照视图同步展示内外运动。
3. **循环演示**：自由点选六个步骤，或使用播放、暂停、上一步、下一步。支持 0.5×、1×、1.5× 速度和可选的连续循环。
4. **结构学习**：点选模型或八个部件按钮查看说明。用滑块分离结构层；感应可用时也可通过倾斜调整。键盘可通过 Tab 和 Enter/空格选择部件。
5. **声音与反馈**：声音默认关闭，可开启并调整音量。振动取决于设备支持；“减少动态效果”遵循系统偏好，也可手动开启。
6. **重置演示**：取消尚未完成的动画、停止感应与播放，保留选定的模型视图和反馈设置。

手机感应需支持的浏览器及 HTTPS（本地开发可用 localhost）。点击“启用感应”后按提示授权，并保持手机静止约一秒。只有收到有效数据并完成静止校准，才会显示“感应已连接”；拒绝授权、无硬件、无数据或校准未完成时，均保留按钮操作。

横竖屏会映射不同的传感器轴；旋转屏幕后重新校准。加速度优先使用浏览器的去重力读数，不可用时使用含重力读数建立静止基线。浏览器仅提供含重力读数时，姿态变化可能影响动作识别；保持握持方向稳定，必要时重新校准或改用按钮。倾斜数据不可用时使用分层滑块。切到后台会暂停感应和播放，返回后需主动恢复；不会自动继续触发反馈。

页面只显示实际收到的读数，按钮操作不会填入模拟加速度或倾斜值。设置与传感器读数仅在当前页面内存中存在，不持久保存。

## 隐私与安全

- 所有逻辑均在浏览器本地运行，不上传、不保存传感器数据。
- 本项目是非品牌化的教育模型，不包含武器制造、改装或实弹操作指导。
- 移动手机时请保持轻柔，并确认周围有足够空间。

## 技术

纯 HTML、CSS、SVG 与原生 JavaScript，浏览器无需下载第三方依赖。`index.html` 维护模型与中文，`locales/en.json` 覆盖英文界面、动态状态、部件说明及无障碍标签。`scripts/localize-game.mjs` 生成完整语言页面；遇到未翻译中文或不适合嵌入源码的翻译会直接报错。

教育站接入地址为 `/games/shotgun/` 和 `/en/games/shotgun/`。两种语言各自返回对应目录，并可直接切换语言。教育站通过其 `scripts/sync-shotgun.mjs` 引入已提交的模型、词典和本地化函数，记录源码提交及每个文件的 SHA-256；此仓库仍是游戏源码的维护入口。教育站与目录 Worker 分别发布，独立的 `alading.org/shotgun/` Worker 不随教育站发布。

## 本地检查

使用任意静态服务器打开根目录，例如 `python3 -m http.server 8765 --bind 127.0.0.1`。

浏览器回归测试需要 Python、Playwright 和 Chromium。可使用已有的 `chromium` / `google-chrome`，或设置 `CHROMIUM_PATH` 指定可执行文件；没有本机浏览器时使用 Playwright 安装的 Chromium。

```sh
node --test --test-isolation=none tests/locales.test.mjs
python3 -m pip install -r tests/requirements.txt
python3 -m playwright install chromium
python3 -m unittest discover -s tests -p '*_test.py' -v
```

测试使用临时本地 HTTP 服务，覆盖完整演示、视图状态、播放控制、不同屏幕布局、权限失败、无效数据、校准、模拟动作、屏幕旋转和后台暂停。传感器事件由测试注入，不能替代 iPhone/Android 真机上的权限、手感、音量和振动验证。测试不连接生产服务。

## alading.org 的 Cloudflare 部署

根目录 `index.html` 是模型源码，英文翻译位于 `locales/en.json`；`cloudflare-deployment/wrangler.jsonc` 保存既有 Worker 和 `/shotgun` 路由设置。准备脚本生成 `/shotgun/` 与 `/shotgun/en/` 两个页面，并设置对应的导航、canonical 和语言互链。部署资产由源码生成，不再手工维护另一份 HTML，也不依赖相邻的 edu 网站目录。

在本仓库根目录执行以下命令准备资产并检查部署（Node.js 22 或更高版本）：

```sh
node cloudflare-deployment/prepare.mjs
npx wrangler@4.92.0 deploy --dry-run --config cloudflare-deployment/wrangler.jsonc
```

正式部署使用同一命令移除 `--dry-run`。部署环境必须单独设置 `CLOUDFLARE_ACCOUNT_ID` 为现有生产账户，并通过 `CLOUDFLARE_API_TOKEN` 提供授权；账户标识和密钥不写入这个公开仓库。部署前保存当前 Worker 版本，发布后核对 `https://alading.org/shotgun/`；需要回退时恢复发布前版本。GitHub Pages 继续直接使用根目录文件。
