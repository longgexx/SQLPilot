# SQLPilot

SQLPilot 是一个基于 LLM Agent 的 SQL 优化与验证平台。它利用大语言模型（LLM）来诊断慢查询，生成优化建议，并通过在影子数据库中执行来严格验证这些建议的有效性。

## 核心功能

- **自动化诊断**: 深入分析执行计划（Explain Plan），精准定位性能瓶颈。
- **智能 SQL 优化**: 提供重写 SQL 或添加索引的专业建议。
- **严格验证机制**:
    - **语义一致性检查**: 确保优化后的 SQL 返回结果与原 SQL 完全一致。
    - **性能提升量化**: 实测执行时间，拒绝“负优化”。
- **灵活的接入方式**: 支持 CLI 命令行工具和 REST API 接口。

## 优化案例展示

**场景**: 查询某以天为维度的订单数据。
**问题**: 在索引列上使用函数 `DATE()` 导致索引失效，引发全表扫描。

### 1. 原始 SQL (低效)
```sql
SELECT * FROM orders WHERE DATE(created_at) = '2023-01-01';
```
❌ **诊断**: `DATE(created_at)` 函数导致无法使用 `created_at` 字段上的索引，触发 **Full Table Scan**。
Time: **1250 ms**

### 2. SQLPilot 优化建议
```sql
SELECT * FROM orders 
WHERE created_at >= '2023-01-01 00:00:00' 
  AND created_at <= '2023-01-01 23:59:59';
```
✅ **优化原理**: 将函数计算转换为范围查询（Range Scan），成功利用索引。

### 3. 验证结果
- **语义检查**: 通过 (结果集 Hash 一致)。
- **性能检查**: Time: **12 ms** (提升 **100倍**)。

## 安装指南

```bash
pip install -r requirements.txt
```

## 配置说明

复制示例配置文件并修改数据库和 LLM 凭证：

```bash
cp config/config.example.yaml config/config.yaml
```

## 使用方法

### 命令行工具 (CLI)

```bash
# 优化单条 SQL
python -m sqlpilot.cli.main optimize --sql "SELECT * FROM orders WHERE DATE(created_at) = '2023-01-01'"

# 系统健康检查
python -m sqlpilot.cli.main health
```

### API 服务

启动服务:

```bash
uvicorn sqlpilot.api.app:app --reload
```

调用优化接口:

```bash
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT ...", "database": "mysql"}'
```

## Docker 部署

```bash
docker-compose up --build
```
