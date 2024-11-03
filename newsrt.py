import os
import sys
import shutil
import zipfile
import tempfile
import configparser
import re

def extract_part_number(filename):
    # 专门匹配 "Part X" 中的数字
    match = re.search(r'Part\s+(\d+)', filename)
    if match:
        return int(match.group(1))
    return 0

def get_next_filename(copy_dest, last_name):
    # 获取目录下所有文件
    files = []
    for f in os.listdir(copy_dest):
        if os.path.isfile(os.path.join(copy_dest, f)) and f.endswith('.mkv'):
            # 只移除.mkv扩展名，保留文件名中的其他点号
            base_name = os.path.splitext(f)[0]
            if base_name not in files:
                files.append(base_name)
    
    # 排序文件列表
    files.sort(key=extract_part_number)
    #print(files)
    
    # 如果last_name为空或不在列表中，返回第一个文件名
    if not last_name or last_name not in files:
        return files[0] if files else None
    
    # 获取last_name的下一个文件名
    current_index = files.index(last_name)
    if current_index + 1 < len(files):
        return files[current_index + 1]
    return None

def read_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return {
        'copy_dest': config['Paths']['copy_dest'],
        'zip_path': config['Paths']['zip_path'],
        'last_name': config['State'].get('last_name', '')
    }

def update_config_last_name(new_name):
    config = configparser.ConfigParser()
    config.read('config.ini')
    config['State']['last_name'] = new_name
    with open('config.ini', 'w') as configfile:
        config.write(configfile)

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
    # 读取配置
    config = read_config()
    
    # 获取下一个文件名
    new_name = get_next_filename(config['copy_dest'], config['last_name'])
    if not new_name:
        print("没有找到合适的文件名")
        sys.exit(1)
    
    # 执行重命名操作
    if rename_subtitle_files(new_name, config['zip_path'], config['copy_dest']):
        # 更新配置文件中的last_name
        update_config_last_name(new_name)
        print("所有操作已完成")
    else:
        print("操作失败")
    #print(get_next_filename(config['copy_dest'], config['last_name']))

if __name__ == "__main__":
    main()
