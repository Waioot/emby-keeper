import argparse
import asyncio
import string
import sys
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from embykeeper.config import config
from embykeeper.llm.ocr import OCRService


def normalize_text(text: str) -> str:
    punctuation = string.punctuation + "，。！？；：、“”‘’（）【】《》〈〉「」『』"
    return text.translate(str.maketrans("", "", punctuation)).replace(" ", "").strip().lower()


async def test_image(image_path: Path):
    data = image_path.read_bytes()
    bio = BytesIO(data)
    bio.name = image_path.name

    ocr = await OCRService.get()
    with ocr:
        raw_result = await ocr.run(bio, gif=image_path.suffix.lower() == ".gif")

    expected = image_path.stem.lower()
    normalized = normalize_text(raw_result or "")
    matched = normalized == expected

    print(f"文件: {image_path}")
    print(f"期望: {expected}")
    print(f"原始结果: {raw_result!r}")
    print(f"归一化结果: {normalized!r}")
    print(f"匹配: {'是' if matched else '否'}")
    print("-" * 60)
    return matched


async def main():
    parser = argparse.ArgumentParser(description="使用项目当前 OCR 逻辑测试图片验证码识别结果")
    parser.add_argument(
        "paths",
        nargs="*",
        default=["test-img"],
        help="图片文件或目录, 默认为 test-img",
    )
    parser.add_argument(
        "--config",
        default="config.toml",
        help="配置文件路径, 默认为 config.toml",
    )
    args = parser.parse_args()

    ok = await config.reload_conf(args.config)
    if not ok:
        raise SystemExit("配置文件加载失败")

    image_paths = []
    for raw_path in args.paths:
        path = Path(raw_path)
        if path.is_dir():
            image_paths.extend(sorted(p for p in path.iterdir() if p.is_file()))
        elif path.is_file():
            image_paths.append(path)

    if not image_paths:
        raise SystemExit("未找到可测试的图片文件")

    provider = OCRService.get_provider_name() or "local"
    print(f"OCR 通道: {provider}")
    print("=" * 60)

    success = 0
    for image_path in image_paths:
        try:
            matched = await test_image(image_path)
        except Exception as e:
            matched = False
            print(f"文件: {image_path}")
            print(f"错误: {e.__class__.__name__}: {e}")
            print("-" * 60)
        success += int(matched)

    print(f"总计: {success}/{len(image_paths)} 匹配")


if __name__ == "__main__":
    asyncio.run(main())
