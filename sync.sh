aws s3 sync s3://zewen-dev-backup/a-evolve/ /home/ec2-user/A-EVOLVE-V2/a-evolve --delete --exclude "*.pyc" --exclude "__pycache__/*" --exclude ".git/*" --exclude "node_modules/*"
aws s3 sync s3://zewen-dev-backup/claude-history/ /home/ec2-user/.claude/projects/-home-ec2-user-A-EVOLVE-V2-a-evolve/ --exclude "*.tmp"


 