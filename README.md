# stackwatch

A CLI tool that monitors AWS CloudFormation stack events in real-time with filtered output and alerting.

---

## Installation

```bash
pip install stackwatch
```

Or install from source:

```bash
git clone https://github.com/yourname/stackwatch.git && cd stackwatch && pip install .
```

---

## Usage

Watch a stack in real-time:

```bash
stackwatch --stack my-production-stack
```

Filter events by status and set up alerts:

```bash
stackwatch --stack my-production-stack --filter FAILED --alert email
```

**Options:**

| Flag | Description |
|------|-------------|
| `--stack` | CloudFormation stack name or ARN |
| `--filter` | Filter events by status (e.g. `FAILED`, `COMPLETE`) |
| `--alert` | Alert method: `email`, `slack`, or `sns` |
| `--region` | AWS region (defaults to profile region) |
| `--interval` | Polling interval in seconds (default: `5`) |
| `--tail` | Number of past events to show on start (default: `0`) |

> **Note:** Ensure your AWS credentials are configured via `~/.aws/credentials` or environment variables before running.

---

## Requirements

- Python 3.8+
- AWS credentials with `cloudformation:DescribeStackEvents` permission

---

## License

This project is licensed under the [MIT License](LICENSE).
