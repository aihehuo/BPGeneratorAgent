# Tests

测试目录包含了项目的单元测试。

## 运行测试

### 运行所有测试

```bash
# 从项目根目录运行
python -m unittest discover tests -v

# 或者运行特定的测试文件
python -m unittest tests.test_input_completeness_node -v
```

### 运行特定的测试类

```bash
python -m unittest tests.test_input_completeness_node.TestInputCompletenessNode -v
```

### 运行特定的测试方法

```bash
python -m unittest tests.test_input_completeness_node.TestInputCompletenessNode.test_init -v
```

## 测试文件

### test_input_completeness_node.py

包含 `InputCompletenessNode` 的单元测试，覆盖：

- 节点初始化
- `/tmp` 目录下的 session 管理
- 检查点名称映射
- JSON 输出处理
- LangChain 集成（如果有）
- 文件系统回退方案
- 完整性和验证逻辑

## 测试依赖

测试使用 Python 标准库的 `unittest` 模块，不需要额外的测试框架。但是，某些测试可能需要 LangChain 库才能完全测试所有功能（如果没有安装，会使用回退方案）。

## Mock 对象

测试使用 Mock LLM 客户端来避免实际调用 LLM API，使测试快速且可重复。

