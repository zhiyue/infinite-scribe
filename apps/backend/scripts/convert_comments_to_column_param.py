#!/usr/bin/env python
"""将 ORM 模型中的行内注释转换为 SQLAlchemy Column 的 comment 参数"""

import re
from pathlib import Path


def convert_inline_comments_to_column_comments(file_path: str):
    """转换文件中的行内注释为 Column comment 参数"""
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # 匹配 Column 定义后面的行内注释
    # 匹配模式: Column(...) # 注释内容
    pattern = r"(Column\([^)]+)\)\s*#\s*([^\n]+)"

    def replace_func(match):
        column_def = match.group(1)
        comment = match.group(2).strip()
        # 转义注释中的双引号
        comment = comment.replace('"', '\\"')
        return f'{column_def}, comment="{comment}")'

    # 执行替换
    new_content = re.sub(pattern, replace_func, content)

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"✅ 已转换文件: {file_path}")


def main():
    """主函数"""
    # 转换 ORM 模型文件
    orm_file = Path(__file__).parent.parent / "src" / "models" / "orm_models.py"

    if orm_file.exists():
        convert_inline_comments_to_column_comments(str(orm_file))
        print("\n转换完成！现在 Column 定义中包含了 comment 参数。")
        print("下次生成 migration 时，这些注释将会包含在数据库表定义中。")
    else:
        print(f"❌ 找不到文件: {orm_file}")


if __name__ == "__main__":
    main()
