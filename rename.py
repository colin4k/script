import os
import re
import glob

def find_and_rename_subtitles():
    # 定义文件名模式
    pattern = r'Takeda\.Shingen\.S01E(\d{2})\.1080p\.AMZN\.WEB-DL\.DD\+2\.0\.H\.264-ARiN\.srt$'
    
    # 获取当前目录下所有.srt文件
    srt_files = glob.glob('*.srt')
    
    # 找出符合模式的文件
    matched_files = []
    for file in srt_files:
        match = re.match(pattern, file)
        if match:
            episode_num = int(match.group(1))
            matched_files.append((episode_num, file))
    
    if not matched_files:
        print("未找到符合模式的字幕文件")
        return
    
    # 按集数排序
    matched_files.sort()
    
    # 向上查找，直到找到不存在 chs 的文件
    for episode_num, target_file in matched_files:
        chs_filename = target_file.replace('.srt', '.chs.srt')
        if not os.path.exists(chs_filename):
            break
    else:
        print("所有匹配的字幕文件都已存在对应的中文字幕文件")
        return
    
    # 检查transcription.srt是否存在
    if not os.path.exists('translation.srt'):
        print("translation.srt 文件不存在")
        return
    
    # 重命名文件
    try:
        print(f"准备重命名 translation.srt 为 {chs_filename}")
        os.rename('translation.srt', chs_filename)
        print(f"已将 translation.srt 重命名为 {chs_filename}")
    except OSError as e:
        print(f"重命名失败: {e}")

if __name__ == '__main__':
    find_and_rename_subtitles()