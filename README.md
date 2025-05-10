# mytoolkit

A lightweight CLI toolkit for managing AWS Auto Scaling Groups (ASGs) with rich interactive UIs.

## Installation

```bash
# Install from PyPI
pip install mytoolkit

# Or install locally in editable mode
git clone <your-repo-url>
cd mytoolkit
pip install -e .

Commands

Command	Description
asg-scale	Interactively scale a single ASG by EC2 “Name” tag
asg-find	Batch-discover ASG names from a JSON list of EC2 names
asg-batch-scale	Generate or execute a batch ASG scaling plan (JSON)

Each command supports --help for full options and examples.

⸻

1. asg-scale

# Show help
asg-scale --help

# Run in default region
asg-scale

# Specify AWS region
asg-scale --region us-west-2

Interactive flow:
	1.	Confirm AWS account & region
	2.	Enter a fuzzy EC2 “Name” tag
	3.	Select one ASG from the list
	4.	Enter new Min/Desired/Max values (with validation)
	5.	Confirm and apply update

Logs: logs/asg-scale/<timestamp>.log

⸻

2. asg-find

# Generate a JSON template
asg-find --get-temp-json

# Discover ASGs from template
asg-find \
  --input-json service_keywords_template.json \
  --region ap-east-1

	•	--get-temp-json writes service_keywords_template.json in current folder:

[
  { "ec2_name": "service1" },
  { "ec2_name": "example-service" }
]


	•	--input-json reads that file and prompts to choose ASG when multiple matches.
	•	Outputs discovered_asgs.json in CWD:

[
  { "ec2_name": "service1", "asg_name": "service1-asg" },
  { "ec2_name": "example-service", "asg_name": null }
]



Logs: logs/asg-find/<timestamp>.log

⸻

3. asg-batch-scale

# Generate a batch scaling template
asg-batch-scale --get-template-json \
  --input-json discovered_asgs.json \
  --region ap-east-1

# Execute the batch plan
asg-batch-scale \
  --input-json logs/asg-batch-scale/batch_scale_template_<timestamp>.json \
  --region ap-east-1

	•	Template format (generated in logs/asg-batch-scale/):

{
  "ng": {
    "asg_name": "nginx-xx-asg",
    "created": "2025-05-09 15:42:46",
    "current": { "n":1, "d":1, "x":3 },
    "target":  { "n":1, "d":1, "x":3 }
  }
}


	•	Execution will validate, confirm, apply updates one-by-one (with triple confirmation), and record:

{
  "ng": {
    "asg_name": "nginx-xx-asg",
    "created": "...",
    "current": { "n":1, "d":1, "x":3 },
    "target":  { "n":2, "d":2, "x":2 },
    "status": "updated",
    "updated_by": "arn:aws:iam::123456789012:user/you",
    "updated_at": "2025-05-10 12:34:56"
  }
}


	•	Results saved to logs/asg-batch-scale/batch_scale_result_<timestamp>.json

⸻

Logging

All commands write detailed logs under:

logs/<command-name>/<YYYYMMDD_HHMMSS>.log
logs/asg-batch-scale/batch_scale_template_<timestamp>.json
logs/asg-batch-scale/batch_scale_result_<timestamp>.json

Use --help for more details on options and workflows.
Happy scaling! 🚀```