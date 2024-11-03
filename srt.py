import os
import sys
import shutil
import zipfile
import tempfile

def rename_subtitle_files(new_name, zip_path, copy_dest):
    try:
        # 创建临时目录用于解压文件
        with tempfile.TemporaryDirectory() as temp_dir:
            # 解压ZIP文件
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                print(f"已成功解压ZIP文件到临时目录")
            except Exception as e:
                print(f"解压ZIP文件时发生错误: {e}")
                return False

            # 确保复制目标路径存在
            if not os.path.exists(copy_dest):
                print(f"错误：复制目标路径 {copy_dest} 不存在")
                return False

            # 定义文件映射关系
            file_mappings = {
                'trans_subtitles.srt': f'{new_name}.chs.srt',
                'src_subtitles.srt': f'{new_name}.en.srt',
                'bilingual_trans_src_subtitles.srt': f'{new_name}.srt'
            }

            # 遍历文件映射进行重命名
            for old_name, new_filename in file_mappings.items():
                old_path = os.path.join(temp_dir, old_name)
                new_path = os.path.join(temp_dir, new_filename)
                copy_path = os.path.join(copy_dest, new_filename)

                if os.path.exists(old_path):
                    try:
                        os.rename(old_path, new_path)
                        print(f"成功将 {old_name} 重命名为 {new_filename}")
                        # 复制文件到新位置
                        shutil.copy2(new_path, copy_path)
                        print(f"已复制：{new_filename} -> {copy_path}")
                    except OSError as e:
                        print(f"重命名或复制文件时发生错误: {e}")
                else:
                    print(f"警告：文件 {old_name} 不存在")

            # 删除原始ZIP文件
            try:
                os.remove(zip_path)
                print(f"已删除原始ZIP文件: {zip_path}")
            except Exception as e:
                print(f"删除ZIP文件时发生错误: {e}")

        # 临时目录会在with语句结束后自动删除
        print("临时文件已清理完成")
        return True

    except Exception as e:
        print(f"发生错误: {e}")
        return False

def main():
    # 检查命令行参数
    if len(sys.argv) != 3:
        print("使用方法: python script.py <copyDestPath> <newName> ")
        sys.exit(1)

    new_name = sys.argv[2]
    copy_dest = sys.argv[1]
    zip_path = '/Users/colin/Downloads/subtitles.zip'

    # 执行重命名操作
    if rename_subtitle_files(new_name, zip_path, copy_dest):
        print("所有操作已完成")
    else:
        print("操作失败")

if __name__ == "__main__":
    main()
