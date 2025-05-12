#!/bin/bash

set -e

OS_TYPE="$(uname -s)"
echo "📦 当前系统: $OS_TYPE"

# 🧩 工具检查函数

check_or_install() {
local name="$1"
local check_cmd="$2"
local install_cmd="$3"
local version_cmd="$4"

echo "🔍 检查 $name..."
if command -v $check_cmd &> /dev/null; then
echo "✅ $name 已安装: $($version_cmd)"
else
echo "📦 安装 $name..."
eval "$install_cmd"
echo "✅ $name 安装成功: $($version_cmd)"
fi
}

# Step 1: 检查 Python

PY_CMD=$(command -v python3 || command -v python)
if [ -z "$PY_CMD" ]; then
echo "❌ 未检测到 Python，请手动安装后重试：https://www.python.org/downloads/"
exit 1
fi
echo "✅ Python 可用: $($PY_CMD --version)"

# Step 2: 检查 pipx

check_or_install "pipx" "pipx" "$PY_CMD -m pip install --user pipx && $PY_CMD -m pipx ensurepath && export PATH=\"\$HOME/.local/bin:\$PATH\"" "pipx --version"

# Step 3: 检查 AWS CLI

if command -v aws &> /dev/null; then
echo "✅ AWS CLI 已安装: $(aws --version)"
else
echo "📦 安装 AWS CLI..."
if [[ "$OS_TYPE" == "Darwin" ]]; then
brew install awscli
elif [[ "$OS_TYPE" == MINGW* ]]; then
echo "❌ Windows 系统请手动安装 AWS CLI v2：https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-windows.html"
exit 1
else
echo "❌ 不支持的系统: $OS_TYPE"
exit 1
fi
echo "✅ AWS CLI 安装成功: $(aws --version)"
fi

# Step 4: 检查 gimme-aws-creds

echo "🔍 检查 gimme-aws-creds..."
if command -v gimme-aws-creds &> /dev/null; then
echo "✅ gimme-aws-creds 已安装: $(gimme-aws-creds --version || echo '版本不支持 --version')"
else
echo "📦 安装 gimme-aws-creds..."
pipx install gimme-aws-creds
echo "✅ 安装成功: $(gimme-aws-creds --version || echo '版本不支持 --version')"
fi

# Step 4.1: 写入配置文件 ~/.okta_aws_login_config（首次写入）

CONFIG_FILE=~/.okta_aws_login_config
if [ -f "$CONFIG_FILE" ]; then
echo "✅ 检测到配置文件 $CONFIG_FILE"
echo "🔍 当前配置如下:"
echo "-----------------------------------------"
cat "$CONFIG_FILE"
echo "-----------------------------------------"
else
echo "⚠️  未发现配置文件，将进行首次配置"
echo -n "👤 请输入你的 Okta 用户名 (如 [Jingcheng.Yang@nike.com](mailto:Jingcheng.Yang@nike.com)): "
read -r OKTA_USERNAME

cat > "$CONFIG_FILE" <<EOF
[DEFAULT]
okta_org_url = [https://nike.okta.com](https://nike.okta.com/)
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

# Step 5: 安装 mytoolkit

echo "🔍 检查 mytoolkit..."
if pipx list | grep -q 'mytoolkit'; then
echo "✅ mytoolkit 已安装"
else
echo "📦 安装 mytoolkit..."
pipx install "git+https://github.com/lovepaul/mytoolkit.git@main"
echo "✅ 安装完成"
fi

echo "🎉 所有环境组件配置完成！"
