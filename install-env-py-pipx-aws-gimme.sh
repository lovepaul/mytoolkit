#!/bin/bash

set -e

OS_TYPE="$(uname -s)"
echo "📦 当前系统: $OS_TYPE"

# 🐍 Step 1: 检查 Python
echo "🔍 检查 Python 安装..."
PY_CMD=$(command -v python3 || command -v python)
if [ -z "$PY_CMD" ]; then
  echo "❌ 未检测到 Python，请安装后重试"
  exit 1
fi
echo "✅ Python 已安装: $($PY_CMD --version)"

# 🧪 Step 2: 安装 pipx
echo "🔍 检查 pipx..."
if ! command -v pipx &> /dev/null; then
  echo "📦 安装 pipx..."
  $PY_CMD -m pip install --user pipx
  $PY_CMD -m pipx ensurepath
  export PATH="$HOME/.local/bin:$PATH"
fi
echo "✅ pipx 版本: $(pipx --version)"

# ☁️ Step 3: AWS CLI
echo "🔍 检查 AWS CLI..."
if ! command -v aws &> /dev/null; then
  echo "📦 安装 AWS CLI..."
  if [[ "$OS_TYPE" == "Darwin" ]]; then
    brew install awscli
  elif [[ "$OS_TYPE" == MINGW* ]]; then
    echo "请手动安装 AWS CLI：https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html"
    exit 1
  else
    echo "❌ 不支持系统: $OS_TYPE"
    exit 1
  fi
fi
echo "✅ AWS CLI 版本: $(aws --version)"

# 🔐 Step 4: 安装 gimme-aws-creds
echo "🔍 安装 gimme-aws-creds..."
pipx install gimme-aws-creds || echo "已安装"
echo "✅ gimme-aws-creds 安装完成"

# 🔧 Step 4.1: 配置文件处理
echo "📝 检查 gimme-aws-creds 配置..."

USER_HOME="$HOME"
CONFIG_DIR="$USER_HOME/.okta"
CONFIG_FILE="$CONFIG_DIR/okta-aws"

if [ -f "$CONFIG_FILE" ]; then
  echo "✅ 检测到现有配置文件: $CONFIG_FILE"
  echo "🔍 当前配置如下:"
  echo "-----------------------------------------"
  cat "$CONFIG_FILE"
  echo "-----------------------------------------"
else
  echo "⚠️  未发现配置文件，将进行首次配置"
  mkdir -p "$CONFIG_DIR"
  
  echo -n "👤 请输入你的 Okta 用户名 (如 Jingcheng.Yang@nike.com): "
  read -r OKTA_USERNAME

  cat > "$CONFIG_FILE" <<EOF
[DEFAULT]
okta_org_url = https://nike.okta.com
okta_auth_server = aus27z7p76as9Dz0H1t7
client_id = 0oa34x20aq50blCCZ1t7
gimme_creds_server = https://gimme-aws-creds.cis-iam-okta-prod.nikecloud.com/list-accounts
aws_appname =
aws_rolename =
write_aws_creds = True
cred_profile = role
okta_username = $OKTA_USERNAME
app_url =
resolve_aws_alias = False
remember_device = True
aws_default_duration = 7200
device_token =
register_device = True
output_format = export
preferred_mfa_type = token:software:totp
preferred_mfa_provider = GOOGLE
EOF

  echo "✅ 配置文件已写入: $CONFIG_FILE"
fi

# 🛠️ Step 5: 安装自定义工具
echo "📦 安装 mytoolkit 工具..."
pipx install "git+https://github.com/lovepaul/mytoolkit.git@main" || echo "已安装"

echo "🎉 环境配置完成！"