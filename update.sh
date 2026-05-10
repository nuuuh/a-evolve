aws s3 sync /home/ec2-user/A-EVOLVE-V2/a-evolve s3://zewen-dev-backup/a-evolve/ --delete --exclude "*.pyc" --exclude "__pycache__/*" --exclude ".git/*" --exclude "node_modules/*"
