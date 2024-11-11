from PIL import Image
import json
from pathlib import Path
import subprocess
import argparse


def find_closest_resolution(width, height, resolutions):
    aspect_ratio = width / height
    min_diff = float("inf")
    closest = "Strange resolution" + f" ({width}x{height})"

    current_pixels = width * height

    for (std_w, std_h), name in resolutions.items():
        std_ratio = std_w / std_h
        ratio_diff = abs(aspect_ratio - std_ratio)
        pixels_diff = abs(current_pixels - (std_w * std_h)) / 1000000

        # Si encuentra una resolución cercana, actualiza closest
        if (ratio_diff < 0.2 or pixels_diff < 2) and pixels_diff < min_diff:
            min_diff = pixels_diff
            closest = name

    return closest


def get_resolution_standard(width, height):
    resolutions = {
        (1280, 720): "HD (720p)",
        (1920, 1080): "Full HD (1080p)",
        (2560, 1440): "2K (1440p)",
        (3840, 2160): "4K (2160p)",
        (7680, 4320): "8K (4320p)",
    }

    # Coincidencia exacta
    exact_match = resolutions.get((width, height))
    if exact_match:
        return exact_match

    # Buscar aproximación
    return find_closest_resolution(width, height, resolutions)


def get_image_resolution(image_path):
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            standard = get_resolution_standard(width, height)
            return width, height, standard
    except Exception as e:
        return f"Error processing {image_path}: {str(e)}"


def get_wallpaper_metadata(wallpaper_dir, metadata_key):
    metadata_file = wallpaper_dir / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
                return metadata.get("KPlugin", {}).get(
                    metadata_key, f"No {metadata_key} available"
                )
        except:
            return "Error reading metadata.json"
    return "No metadata.json found"


def is_directory_empty(directory):
    return not any(directory.iterdir())


def display_image(image_path):
    try:
        subprocess.run(["wezterm", "imgcat", "--width", "50", str(image_path)])
    except subprocess.SubprocessError:
        print(f"Error displaying image: {image_path}")


def get_user_confirmation(message="Press Enter to continue..."):
    input(message)
    return True


def process_image_directory(directory, label=""):
    if not directory.exists() or is_directory_empty(directory):
        if label == "Dark":
            print("Warning: Dark theme images not found or directory is empty")
        return []

    images = []
    for file_path in directory.glob("*"):
        if file_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
            images.append((label, file_path))

    return images


def format_metadata_value(value):
    """Format metadata values for display"""
    if isinstance(value, list):
        return "\n  - " + "\n  - ".join(str(item) for item in value)
    return str(value)


def get_all_metadata(wallpaper_dir):
    """Get all metadata from metadata.json"""
    metadata_file = wallpaper_dir / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                return json.load(f)
        except:
            return {"error": "Error reading metadata.json"}
    return {"error": "No metadata.json found"}


def get_filtered_metadata(wallpaper_dir, show_authors=False):
    """Get specific metadata fields from metadata.json"""
    metadata_file = wallpaper_dir / "metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
                kplugin = metadata.get("KPlugin", {})
                fields = [
                    "Id",
                    "License",
                    "Name",
                    "Name[es]",
                    "Description",
                    "Description[es]",
                ]

                result = {k: kplugin.get(k, "N/A") for k in fields}

                # Handle authors separately
                if show_authors:
                    authors = kplugin.get("Authors", [])
                    if isinstance(authors, list):
                        authors_info = []
                        for author in authors:
                            author_str = f"{author.get('Name', 'N/A')} <{author.get('Email', 'N/A')}>"
                            authors_info.append(author_str)
                        result["_authors"] = (
                            authors_info  # Store authors separately with special key
                        )

                return result
        except:
            return {"error": "Error reading metadata.json"}
    return {"error": "No metadata.json found"}


def process_screenshot(directory):
    screenshot_path = directory / "screenshot.png"
    if screenshot_path.exists() and screenshot_path.is_file():
        print("\n--- Screenshot ---")
        display_image(screenshot_path)
    else:
        print("No screenshot found")


def scan_folder_structure(parent_folder, show_authors=False):
    parent_path = Path(parent_folder)

    for wallpaper_dir in parent_path.iterdir():
        if not wallpaper_dir.is_dir():
            continue

        content_dir = wallpaper_dir / "contents"
        if not content_dir.exists():
            continue

        print(f"\n=== Processing wallpaper: {wallpaper_dir.name} ===")

        # Show filtered metadata
        metadata = get_filtered_metadata(wallpaper_dir, show_authors)
        print("\nMetadata:")
        for key, value in metadata.items():
            if key != "_authors":  # Skip authors in metadata section
                print(f"  {key}: {value}")

        # Show authors section if available
        if show_authors and "_authors" in metadata:
            print("\nAuthors:")
            for author in metadata["_authors"]:
                print(f"  {author}")

        # Collect images from both directories
        image_dir = content_dir / "images"
        image_dark_dir = content_dir / "image_dark"

        images = []
        images.extend(process_image_directory(image_dir, "Light"))
        images.extend(process_image_directory(image_dark_dir, "Dark"))

        if not images:
            print("No valid images found in this wallpaper directory")
            continue

        # Display all collected images
        for label, image_path in images:
            print(f"\n--- {label} Image {get_image_resolution(image_path)[2]} ---")
            display_image(image_path)

        # Display screenshot
        process_screenshot(content_dir)

        # Wait for confirmation after showing all images
        get_user_confirmation("\nPress Enter to continue to next wallpaper...")


def get_wallpapers_directory():
    """Get the wallpapers directory from the script's location"""
    current_file = Path(__file__).resolve()
    # Since script is in /wallpapers/check.py, parent is wallpapers dir
    wallpapers_dir = current_file.parent

    if not wallpapers_dir.exists():
        raise FileNotFoundError(f"Wallpapers directory not found at {wallpapers_dir}")

    return wallpapers_dir


def process_single_wallpaper(wallpaper_dir, show_authors=False):
    """Process a single wallpaper directory"""
    wallpaper_path = Path(wallpaper_dir)
    if not wallpaper_path.is_dir():
        raise ValueError(f"Not a directory: {wallpaper_path}")

    content_dir = wallpaper_path / "contents"
    if not content_dir.exists():
        raise ValueError(f"No contents directory found in {wallpaper_path}")

    print(f"\n=== Processing wallpaper: {wallpaper_path.name} ===")

    # Show filtered metadata
    metadata = get_filtered_metadata(wallpaper_path, show_authors)
    print("\nMetadata:")
    for key, value in metadata.items():
        if key != "_authors":  # Skip authors in metadata section
            print(f"  {key}: {value}")

    # Show authors section if available
    if show_authors and "_authors" in metadata:
        print("\nAuthors:")
        for author in metadata["_authors"]:
            print(f"  {author}")

    # Process images
    image_dir = content_dir / "images"
    image_dark_dir = content_dir / "image_dark"

    images = []
    images.extend(process_image_directory(image_dir, "Light"))
    images.extend(process_image_directory(image_dark_dir, "Dark"))

    if not images:
        print("No valid images found in this wallpaper directory")
        return

    # Display images
    for label, image_path in images:
        print(f"\n--- {label} Image {get_image_resolution(image_path)[2]} ---")
        display_image(image_path)

    # Display screenshot
    process_screenshot(content_dir)


def main():
    parser = argparse.ArgumentParser(description="Check wallpaper metadata and images")
    parser.add_argument("folder", nargs="?", help="Specific wallpaper folder to check")
    parser.add_argument(
        "-a", "--authors", action="store_true", help="Show authors information"
    )
    args = parser.parse_args()

    try:
        if args.folder:
            # Process single folder
            process_single_wallpaper(args.folder, args.authors)
        else:
            # Process all wallpapers
            parent_folder = get_wallpapers_directory()
            scan_folder_structure(parent_folder, args.authors)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
