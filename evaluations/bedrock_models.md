# Bedrock Models: Agentic Compatibility

Models tested for drop-in replacement of Claude Sonnet 4.6 in A-EVOLVE-V2.
All tests use the Bedrock Converse API with native tool calling.

## Test Results

| Model | ID | Basic | Tool call | Tool exec | Multi-tool | Drop-in? |
|---|---|---|---|---|---|---|
| **Claude Sonnet 4.6** | `us.anthropic.claude-sonnet-4-6` | PASS | PASS | PASS | PASS | **Reference** |
| **DeepSeek V3.2** | `deepseek.v3.2` | PASS | PASS | PASS | PASS | **Yes** |
| **Llama 3.1 70B** | `us.meta.llama3-1-70b-instruct-v1:0` | PASS | PASS | PASS | PASS | **Yes** |
| **Llama 3.3 70B** | `us.meta.llama3-3-70b-instruct-v1:0` | PASS | PASS | PASS | PASS | **Yes** |
| **Mistral Devstral 123B** | `mistral.devstral-2-123b` | PASS | PASS | PASS | PASS | **Yes** |
| **Amazon Nova Lite** | `amazon.nova-lite-v1:0` | PASS | PASS | PASS | PASS | **Yes** |
| **Qwen3 32B** | `qwen.qwen3-32b-v1:0` | PASS | PASS | PASS | PASS | **Yes** |
| **Kimi K2.5** | `moonshotai.kimi-k2.5` | PASS | PASS | PASS | PASS | **Yes** |
| **Nemotron Super 120B** | `nvidia.nemotron-super-3-120b` | PASS | PASS | PASS | PASS | **Yes** |
| **GLM-5** | `zai.glm-5` | PASS | PASS | PASS | PASS | **Yes** |
| **GLM-4.7** | `zai.glm-4.7` | PASS | PASS | PASS | PASS | **Yes** |
| **Command R+** | `cohere.command-r-plus-v1:0` | PASS | PASS | PASS | PASS | **Yes** |
| Llama 4 Scout 17B | `us.meta.llama4-scout-17b-instruct-v1:0` | PASS | PASS | FAIL | PASS | No |
| Llama 4 Maverick 17B | `us.meta.llama4-maverick-17b-instruct-v1:0` | PASS | PASS | FAIL | PASS | No |
| Jamba 1.5 Large | `ai21.jamba-1-5-large-v1:0` | PASS | PASS | SKIP | SKIP | No |
| Claude Haiku 3.5 | `anthropic.claude-3-5-haiku-20241022-v1:0` | SKIP | SKIP | SKIP | SKIP | Not enabled |

## Tests

- **Basic**: Answer "What is the capital of France?" correctly
- **Tool call**: Return native `toolUse` block when given a calculator tool
- **Tool exec**: Full loop — call tool, receive result, produce final answer using result
- **Multi-tool**: Select the correct tool (calculator vs weather vs submit) based on the query

## Drop-in Compatible (12 models)

To use any of these models, change `model_name` in the experiment config YAML:

```yaml
# experiments/futurex/configs/baseline.yaml
model_name: deepseek.v3.2   # or any ID from the table above
```

## Not Compatible

| Model | Issue |
|---|---|
| Llama 4 Scout/Maverick | Can call tools but returns empty response after receiving tool results |
| Jamba 1.5 Large | Tool calling works but tool execution loop not tested (different response format) |
| Claude Haiku 3.5 | Not enabled in current AWS account |
| Gemma 3 27B | Outputs tool calls as text, not native `toolUse` blocks |
| MiniMax M2.5 | Returns empty responses |
| Kimi K2 Thinking | Returns empty responses |
| DeepSeek R1 | On-demand throughput not supported |
| Llama (direct IDs) | Must use inference profile IDs (`us.meta.*` prefix) |
