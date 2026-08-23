# -*- coding: utf-8 -*-
"""
transcode_all.py
批量转码服务器上所有视频，统一转为浏览器通用格式 (H.264 + AAC + faststart)。
- 已兼容的视频自动跳过（秒级处理）
- HEVC/H265 等不兼容视频自动转码
用法：
    cd E:\DjangoProject
    .venv\Scripts\activate
    python transcode_all.py
"""

import os
import subprocess
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DjangoProject.settings')
django.setup()

from django.conf import settings  # noqa: E402


# ============================================================
# 工具函数（与 works/views.py 保持一致）
# ============================================================

def run_cmd(cmd, timeout=900):
    """执行命令，返回 (成功?, 错误信息)"""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode == 0, result.stderr
    except FileNotFoundError:
        return False, '未找到 ffmpeg/ffprobe，请确认已安装并加入 PATH'
    except subprocess.TimeoutExpired:
        return False, '命令执行超时'
    except Exception as e:
        return False, str(e)


def get_codec(path, stream_type):
    """用 ffprobe 检测指定流(v/a)的编码名"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', f'{stream_type}:0',
        '-show_entries', 'stream=codec_name',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        path,
    ]
    ok, _ = run_cmd(cmd, timeout=60)
    if not ok:
        return ''
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60
        ).stdout
        return out.strip().split('\n')[0].strip()
    except Exception:
        return ''


def transcode_video(source_path):
    """
    转码单个视频为 H.264 + AAC + faststart。
    返回 (成功?, 最终路径)。失败时保留原文件。
    """
    if not os.path.exists(source_path):
        return False, source_path

    video_codec = get_codec(source_path, 'v')
    audio_codec = get_codec(source_path, 'a')

    dir_name = os.path.dirname(source_path)
    base, ext = os.path.splitext(os.path.basename(source_path))
    tmp_path = os.path.join(dir_name, f'.transcoding_{base}{ext or ".mp4"}')

    already_compatible = video_codec == 'h264' and audio_codec in ('aac', '')

    if already_compatible:
        # 已兼容：只做 remux（快，秒级），并把 moov 移到文件头
        cmd = ['ffmpeg', '-y', '-i', source_path,
               '-c', 'copy', '-movflags', '+faststart', tmp_path]
    else:
        # 不兼容：完整转码为 H.264 + AAC
        cmd = ['ffmpeg', '-y', '-i', source_path,
               '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23',
               '-c:a', 'aac', '-b:a', '128k',
               '-movflags', '+faststart', tmp_path]

    ok, err = run_cmd(cmd)
    if ok and os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
        os.replace(tmp_path, source_path)  # 用转码结果替换原文件
        return True, source_path

    # 失败清理临时文件，保留原文件
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    return False, source_path


# ============================================================
# 主逻辑：遍历 media/works/videos 下所有视频
# ============================================================

def main():
    videos_dir = os.path.join(settings.MEDIA_ROOT, 'works', 'videos')

    if not os.path.exists(videos_dir):
        print(f'❌ 未找到视频目录: {videos_dir}')
        sys.exit(1)

    # 收集所有视频文件
    video_exts = {'.mp4', '.mov', '.webm', '.mkv', '.avi', '.flv', '.m4v'}
    files = []
    for root, _, fnames in os.walk(videos_dir):
        for f in fnames:
            if f.startswith('.transcoding_'):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in video_exts:
                files.append(os.path.join(root, f))

    if not files:
        print('📭 未找到任何视频文件')
        return

    print(f'🔍 共找到 {len(files)} 个视频文件\n')

    transcoded = 0
    skipped = 0
    failed = 0

    for path in sorted(files):
        v_codec = get_codec(path, 'v')
        a_codec = get_codec(path, 'a')

        if v_codec == 'h264' and a_codec in ('aac', ''):
            print(f'✅ 已兼容，跳过: {os.path.basename(path)}')
            skipped += 1
            continue

        print(f'🔄 转码中: {os.path.basename(path)}  '
              f'(视频={v_codec} 音频={a_codec})')
        ok, _ = transcode_video(path)
        if ok:
            print('   ✅ 完成')
            transcoded += 1
        else:
            print('   ❌ 失败（已保留原文件）')
            failed += 1

    print('\n========== 结果汇总 ==========')
    print(f'✅ 转码成功: {transcoded} 个')
    print(f'⏭ 已跳过(本来就兼容): {skipped} 个')
    print(f'❌ 转码失败: {failed} 个')


if __name__ == '__main__':
    main()