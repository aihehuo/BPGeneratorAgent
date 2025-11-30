# Tests

测试目录包含了项目的单元测试，包括使用Mock LLM的快速测试和使用真实LLM API的提示词验证测试。

## 运行测试

### 运行所有测试

```bash
# 从项目根目录运行
python -m unittest discover tests -v

# 或者运行特定的测试文件
python tests/test_input_completeness_node.py -v
python tests/test_bp_structure_node.py -v
```

### 运行特定的测试类

```bash
# Mock测试
python tests/test_input_completeness_node.py TestInputCompletenessNode -v
python tests/test_bp_structure_node.py TestBPStructureNode -v

# 真实LLM测试
python tests/test_input_completeness_node.py TestInputCompletenessNodeWithRealLLM -v
python tests/test_bp_structure_node.py TestBPStructureNodeWithRealLLM -v
```

### 运行特定的测试方法

```bash
python tests/test_input_completeness_node.py TestInputCompletenessNode.test_init -v
python tests/test_bp_structure_node.py TestBPStructureNode.test_run_basic -v
```

## 测试文件

### test_input_completeness_node.py

包含 `InputCompletenessNode` 的单元测试，覆盖：

- **Mock测试（TestInputCompletenessNode）**：
  - 节点初始化
  - 检查点名称映射
  - JSON 输出处理
  - 完整性和验证逻辑
  - previous_inputs 合并功能

- **真实LLM测试（TestInputCompletenessNodeWithRealLLM）**：
  - 完整的中文/英文输入测试
  - 不完整输入测试
  - 输出格式验证（包含markdown_summary）
  - 提示词有效性验证
  - previous_inputs 合并验证

### test_bp_structure_node.py

包含 `BPStructureNode` 的单元测试，覆盖：

- **Mock测试（TestBPStructureNode）**：
  - 节点初始化
  - 输入验证
  - BP结构生成
  - 根据反馈重新生成
  - 输出格式处理（新旧格式兼容）

- **真实LLM测试（TestBPStructureNodeWithRealLLM）**：
  - 中文/英文BP结构生成
  - 输出格式验证（包含markdown_summary）
  - 提示词有效性验证（是否符合精益创业理念）
  - 根据反馈重新生成验证

## Mock 测试

测试使用 Mock LLM 客户端来避免实际调用 LLM API，使测试快速且可重复。这些测试主要用于验证：

- 节点逻辑的正确性
- 输入输出格式处理
- 错误处理机制
- 数据验证逻辑

## 真实LLM测试

真实LLM测试会调用真实的LLM API，主要用于验证提示词（prompts）的有效性。

### 前置条件

1. **配置API密钥**：确保已正确配置LLM API密钥
   - DeepSeek: 设置 `DEEPSEEK_API_KEY` 环境变量或在 `config.py` 中配置
   - OpenAI: 设置 `OPENAI_API_KEY` 环境变量或在 `config.py` 中配置
   - Qwen: 设置 `QWEN_API_KEY` 环境变量或在 `config.py` 中配置

2. **配置文件**：确保 `config.py` 中正确设置了 `default_llm_provider` 和对应的API密钥

### 运行真实LLM测试

#### 方式1：运行所有真实LLM测试

```bash
# Input Completeness Node
python tests/test_input_completeness_node.py TestInputCompletenessNodeWithRealLLM

# BP Structure Node
python tests/test_bp_structure_node.py TestBPStructureNodeWithRealLLM
```

#### 方式2：运行特定的真实LLM测试

```bash
# Input Completeness Node 测试示例
python tests/test_input_completeness_node.py TestInputCompletenessNodeWithRealLLM.test_real_llm_complete_input_chinese
python tests/test_input_completeness_node.py TestInputCompletenessNodeWithRealLLM.test_real_llm_output_format

# BP Structure Node 测试示例
python tests/test_bp_structure_node.py TestBPStructureNodeWithRealLLM.test_real_llm_generate_chinese_bp_structure
python tests/test_bp_structure_node.py TestBPStructureNodeWithRealLLM.test_real_llm_prompt_effectiveness
```

#### 方式3：跳过真实LLM测试

如果不想运行真实LLM测试（例如在CI/CD中），可以设置环境变量：

```bash
export SKIP_REAL_LLM_TESTS=1
python tests/test_input_completeness_node.py
python tests/test_bp_structure_node.py
```

### 真实LLM测试验证内容

#### Input Completeness Node 测试

1. **test_real_llm_complete_input_chinese** - 测试完整的中文商业创意输入
   - 验证输出结构完整性
   - 验证markdown_summary字段存在且非空
   - 验证is_complete应为True

2. **test_real_llm_incomplete_input_chinese** - 测试不完整的中文输入
   - 验证正确识别为不完整（is_complete应为False）
   - 验证提供改进建议

3. **test_real_llm_complete_input_english** - 测试完整的英文商业创意输入
   - 验证markdown_summary使用英文生成（语言一致性）
   - 验证输出格式正确

4. **test_real_llm_prompt_structure** - 验证提示词结构
   - 验证每个视角都有正确的结构
   - 验证completeness值符合预期
   - 验证checklist结构正确

5. **test_real_llm_output_format** - 验证输出格式
   - 验证markdown_summary字段存在
   - 验证markdown_summary非空且格式正确

6. **test_real_llm_with_previous_inputs** - 验证previous_inputs合并
   - 验证合并历史输入后，完整性检查更准确
   - 验证previous_inputs被正确合并到prompt中

#### BP Structure Node 测试

1. **test_real_llm_generate_chinese_bp_structure** - 测试生成中文BP结构
   - 验证生成至少3个核心段落
   - 验证每个段落包含title和content
   - 验证markdown_summary存在且非空
   - 验证标题使用中文

2. **test_real_llm_generate_english_bp_structure** - 测试生成英文BP结构
   - 验证生成至少3个核心段落
   - 验证标题和markdown_summary使用英文（语言一致性）

3. **test_real_llm_output_format_with_markdown_summary** - 验证输出格式
   - 验证包含markdown_summary字段
   - 验证markdown_summary非空且格式正确

4. **test_real_llm_prompt_effectiveness** - 验证提示词有效性
   - 验证生成的结构是否符合精益创业理念
   - 验证包含关键概念（用户画像/痛点、解决方案、MVP等）
   - 验证段落内容与商业创意相关

5. **test_real_llm_regenerate_with_feedback** - 测试根据反馈重新生成
   - 验证能够根据评估反馈重新生成BP结构
   - 验证重新生成的结构与初始结构不同

### 提示词验证要点

真实LLM测试主要用于验证：

1. **提示词有效性**：LLM能否理解提示词并生成符合schema的输出
2. **语言一致性**：LLM生成的markdown_summary是否使用与输入相同的语言
3. **输出格式**：输出是否符合定义的JSON schema（包括新的markdown_summary字段）
4. **逻辑正确性**：节点逻辑是否准确（例如：完整输入通过，不完整输入不通过）

## 测试依赖

测试使用 Python 标准库的 `unittest` 模块，不需要额外的测试框架。但是：

- **Mock测试**：不需要任何外部依赖，可以快速运行
- **真实LLM测试**：需要配置LLM API密钥，某些测试可能需要 LangChain 库才能完全测试所有功能（如果没有安装，会使用回退方案）

## 注意事项

### Mock测试
- 测试快速且可重复
- 不消耗API额度
- 适合CI/CD环境

### 真实LLM测试
1. **API费用**：运行真实LLM测试会消耗API额度，请注意成本
2. **网络要求**：需要能够访问LLM API（可能需要代理）
3. **测试时间**：真实LLM测试比Mock测试慢，请耐心等待
4. **API限制**：注意API速率限制，避免并发过多请求
5. **自动跳过**：如果没有配置API Key，测试会自动跳过，不会导致失败

## 调试技巧

如果测试失败，可以：

1. **Mock测试失败**：
   - 检查测试用例的预期值是否正确
   - 检查Mock LLM的响应格式是否符合节点期望
   - 查看测试输出的详细日志

2. **真实LLM测试失败**：
   - 检查API密钥是否正确配置
   - 检查网络连接（可能需要代理）
   - 查看测试输出的详细日志
   - 检查LLM返回的原始响应是否符合预期
   - 验证提示词是否清晰明确
   - 检查输出是否符合JSON schema要求

## 测试覆盖率

当前测试覆盖的节点：

- ✅ Input Completeness Node（输入完整性检查节点）
- ✅ BP Structure Node（BP结构生成节点）
- 🔄 其他节点测试（待添加）

每个节点都包含：
- Mock测试（快速验证逻辑）
- 真实LLM测试（验证提示词有效性）
