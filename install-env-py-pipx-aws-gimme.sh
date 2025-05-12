#!/bin/bash

set -e

CONFIG_FILE=~/.okta_aws_login_config

# Step 0: 检查配置文件 ~/.okta_aws_login_config
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
preferred_mfa_type = push
preferred_mfa_provider = GOOGLE
EOF

  echo "✅ 配置文件已写入: $CONFIG_FILE"
fi

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
echo "🔍 检查 pipx 是否已安装..."
if command -v pipx &> /dev/null; then
  echo "✅ pipx 已安装: $(pipx --version)"
else
  echo "📦 pipx 未安装，开始安装..."
  $PY_CMD -m pip install --user pipx
  echo "✅ pipx 安装完成"

  echo "🔧 配置 pipx 路径..."
  $PY_CMD -m pipx ensurepath

  echo "🔄 重新加载环境变量..."
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    if [[ -f ~/.bash_profile ]]; then
      sed -i 's|C:\\|/c/|g' ~/.bash_profile
      sed -i 's|\\|/|g' ~/.bash_profile
      source ~/.bash_profile
    fi
  else
    if [[ -f ~/.bashrc ]]; then
      sed -i 's|C:\\|/c/|g' ~/.bashrc
      sed -i 's|\\|/|g' ~/.bashrc
      source ~/.bashrc
    fi
  fi
  echo "✅ 环境变量已重新加载"
fi

# Step 3: 检查 AWS CLI
if command -v aws &> /dev/null; then
  echo "✅ AWS CLI 已安装: $(aws --version)"
else
  echo "📦 安装 AWS CLI..."
  if [[ "$OS_TYPE" == "Darwin" ]]; then
    curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
    sudo installer -pkg AWSCLIV2.pkg -target /
    rm AWSCLIV2.pkg
  elif [[ "$OS_TYPE" == MINGW* || "$OS_TYPE" == "CYGWIN"* ]]; then
    msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi /qn
  else
    echo "❌ 不支持的系统: $OS_TYPE"
    exit 1
  fi
  echo "✅ AWS CLI 安装成功: $(aws --version)"
fi

# Step 4: 配置 AWS CLI
echo "🔧 配置 AWS CLI..."
aws configure set aws_access_key_id "ASIA2V4C3DVB6Q5CDX4Z"
aws configure set aws_secret_access_key "IGiOULEF4LBlf9RQYjpcQXmS21uHnwQoXfztxzts"
aws configure set region "cn-northwest-1"
aws configure set output "json"
echo "✅ AWS CLI 配置完成"

# Step 5: 检查 gimme-aws-creds
echo "🔍 检查 gimme-aws-creds..."
if command -v gimme-aws-creds &> /dev/null; then
  echo "✅ gimme-aws-creds 已安装: $(gimme-aws-creds --version || echo '版本不支持 --version')"
else
  echo "📦 安装 gimme-aws-creds..."
  pip install gimme-aws-creds
  echo "✅ 安装成功: $(gimme-aws-creds --version || echo '版本不支持 --version')"
fi

# Step 6: 安装 mytoolkit
echo "🔍 检查 mytoolkit..."
if pipx list | grep -q 'mytoolkit'; then
  echo "✅ mytoolkit 已安装"
else
  echo "📦 安装 mytoolkit..."
  pipx install "git+https://github.com/lovepaul/mytoolkit.git@main"
  echo "✅ 安装完成"
fi

echo "🎉 所有环境组件配置完成！"
