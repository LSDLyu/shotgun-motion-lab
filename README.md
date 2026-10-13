# Shotgun Motion Lab / 霰弹枪动作实验室

一个适合手机浏览器的互动教育网页：通过轻拉、轻推与轻顿动作，观察泵动式结构的抽象剖面和非品牌化外观模型如何完成退壳、抬弹、闭锁与击发反馈。

## 在线演示

GitHub Pages：<https://lsdlyu.github.io/shotgun-motion-lab/>

## 使用方法

1. 用手机打开在线演示，并点击“启用感应”。
2. 在“示意图 / 外观图”之间切换。
3. 轻拉模拟解锁与退壳，轻推模拟抬弹与闭锁。
4. 闭锁后向后轻顿，触发程序化声效、振动与视觉反馈。

桌面浏览器可以使用页面右侧按钮完成同样的演示。iPhone/iPad 需要在 HTTPS 页面中由用户点击按钮后授权动作传感器。

## 隐私与安全

- 所有逻辑均在浏览器本地运行，不上传、不保存传感器数据。
- 本项目是非品牌化的教育模型，不包含武器制造、改装或实弹操作指导。
- 移动手机时请保持轻柔，并确认周围有足够空间。

## 技术

纯 HTML、CSS、SVG 与原生 JavaScript，无需构建步骤或后端服务，可直接部署到 GitHub Pages、Cloudflare Pages 或任意静态主机。

## alading.org 的 Cloudflare 部署

根目录 `index.html` 是唯一需要维护的页面源码；`cloudflare-deployment/wrangler.jsonc` 保存既有 Worker 和 `/shotgun` 路由设置。部署资产由源码生成，不再手工维护另一份 HTML，也不依赖相邻的 edu 网站目录。

在本仓库根目录执行以下命令准备资产并检查部署（Node.js 22 或更高版本）：

```sh
node cloudflare-deployment/prepare.mjs
npx wrangler@4.92.0 deploy --dry-run --config cloudflare-deployment/wrangler.jsonc
```

正式部署使用同一命令移除 `--dry-run`。部署环境必须单独设置 `CLOUDFLARE_ACCOUNT_ID` 为现有生产账户，并通过 `CLOUDFLARE_API_TOKEN` 提供授权；账户标识和密钥不写入这个公开仓库。部署前保存当前 Worker 版本，发布后核对 `https://alading.org/shotgun/`；需要回退时恢复发布前版本。GitHub Pages 继续直接使用根目录文件。
