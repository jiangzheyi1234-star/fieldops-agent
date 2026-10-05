# 实际验证记录

验证日期：2026-10-05。

## 工程检查

- 17 项 API 与协议测试通过：12 类场景、审批/重复执行、持久化、非法工具和方案证据约束。
- Ruff 检查、TypeScript 检查、Prettier 检查与 Vite 构建通过。
- 固定 72 例测试集、4 方法共 288 次运行；逐例评分和汇总一致性门禁通过。
- Windows 和 Ubuntu 的 GitHub Actions 验证通过。
- GitHub Actions 中实际构建并启动 Docker 容器，通过真实 HTTP 工单、四项审批修复、七项验收及 ZIP 哈希核验。

[首次完整 CI 运行](https://github.com/jiangzheyi1234-star/fieldops-agent/actions/runs/37291982370)记录上述跨平台和容器检查；[最新运行](https://github.com/jiangzheyi1234-star/fieldops-agent/actions)记录后续变动。

## 界面验证

本地浏览器验证了创建复合故障、六条诊断证据、审批、执行、七项验收和 ZIP 下载。内容漂移案例保留两项回答检查失败并进入人工复核。公开 Pages 演示验证了记录加载、新建工单、诊断、审批和最终验收状态。

## 尚未验证

真实模型质量、真实向量数据库/云集群、生产多用户权限、远程设备联调和用户培训效果均没有测评成绩。模型协议测试使用模拟提供方；公开演示是记录回放。
