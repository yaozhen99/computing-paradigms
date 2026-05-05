#!/bin/bash

# AI协作外骨骼协议安装脚本
# 用法: ./install.sh /path/to/your/project

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_TEMPLATES="$SCRIPT_DIR/../templates"

# 检查参数
if [ -z "$1" ]; then
    echo -e "${RED}错误: 请指定目标项目路径${NC}"
    echo "用法: $0 /path/to/your/project"
    exit 1
fi

TARGET_ROOT="$1"

# 检查目标路径是否存在
if [ ! -d "$TARGET_ROOT" ]; then
    echo -e "${YELLOW}目标目录不存在，是否创建? (y/n)${NC}"
    read -r answer
    if [ "$answer" = "y" ]; then
        mkdir -p "$TARGET_ROOT"
        echo -e "${GREEN}已创建目录: $TARGET_ROOT${NC}"
    else
        exit 1
    fi
fi

# 检查源模板目录
if [ ! -d "$SOURCE_TEMPLATES" ]; then
    echo -e "${RED}错误: 源模板目录不存在: $SOURCE_TEMPLATES${NC}"
    exit 1
fi

echo -e "${GREEN}开始安装 AI协作外骨骼协议...${NC}"
echo "源目录: $SOURCE_TEMPLATES"
echo "目标目录: $TARGET_ROOT"
echo ""

# 复制函数，带冲突处理
copy_with_conflict_check() {
    local src="$1"
    local dst="$2"
    
    if [ -e "$dst" ]; then
        echo -e "${YELLOW}文件已存在: $dst${NC}"
        echo "   [s] 跳过  [o] 覆盖  [b] 备份后覆盖  [q] 退出"
        read -r -n 1 choice
        echo ""
        case "$choice" in
            s|S)
                echo "   → 跳过"
                return 1
                ;;
            o|O)
                echo "   → 覆盖"
                rm -rf "$dst"
                ;;
            b|B)
                backup="${dst}.backup.$(date +%Y%m%d_%H%M%S)"
                echo "   → 备份至 $backup 后覆盖"
                mv "$dst" "$backup"
                ;;
            q|Q)
                echo "   → 退出安装"
                exit 0
                ;;
            *)
                echo "   → 无效选择，跳过"
                return 1
                ;;
        esac
    fi
    
    cp -r "$src" "$dst"
    echo -e "${GREEN}   ✓ 已安装: $dst${NC}"
    return 0
}

# 遍历源目录并复制
echo "正在复制模板文件..."
cd "$SOURCE_TEMPLATES"

# 使用 find 遍历所有文件和目录
find . -type f -o -type d | while read -r item; do
    # 跳过当前目录符号
    [ "$item" = "." ] && continue
    
    src_path="$SOURCE_TEMPLATES/$item"
    dst_path="$TARGET_ROOT/$item"
    
    # 确保目标父目录存在
    dst_parent=$(dirname "$dst_path")
    if [ ! -d "$dst_parent" ]; then
        mkdir -p "$dst_parent"
    fi
    
    # 复制文件或目录
    if [ -f "$src_path" ]; then
        copy_with_conflict_check "$src_path" "$dst_path"
    elif [ -d "$src_path" ]; then
        # 目录只创建，不覆盖询问
        if [ ! -d "$dst_path" ]; then
            mkdir -p "$dst_path"
            echo -e "${GREEN}   ✓ 已创建目录: $dst_path${NC}"
        fi
    fi
done

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}AI协作外骨骼协议安装完成！${NC}"
echo -e "${GREEN}==================================${NC}"
echo ""
echo "下一步操作："
echo "1. 进入项目目录: cd $TARGET_ROOT"
echo "2. 检查并配置协议: 查看 AGENTS.md 确认版本和规则"
echo "3. 初始化项目文档: 根据需要填写 docs/architecture.md 等"
echo "4. 启动 AI 助手: 运行 Claude Code 或对应工具，AI 将自动读取协议"
echo ""
echo -e "${YELLOW}提示: 建议将 AGENTS.md 和 docs/ 目录纳入 Git 版本控制${NC}"