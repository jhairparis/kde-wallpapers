import subprocess
import time
import pyautogui
from pathlib import Path
from PIL import Image, ImageDraw
import argparse
import shutil
import json


def get_git_config():
    try:
        name = subprocess.check_output(["git", "config", "user.name"]).decode().strip()
        email = (
            subprocess.check_output(["git", "config", "user.email"]).decode().strip()
        )
        return name, email
    except:
        return "", ""


def create_wallpaper_structure(wallpaper_name, light_image_path, dark_image_path=None):
    wallpapers_dir = Path(__file__).resolve().parent
    wallpaper_dir = wallpapers_dir / wallpaper_name
    contents_dir = wallpaper_dir / "contents"
    images_dir = contents_dir / "images"
    image_dark_dir = contents_dir / "image_dark"

    # Create directories
    images_dir.mkdir(parents=True, exist_ok=True)
    if dark_image_path:
        image_dark_dir.mkdir(parents=True, exist_ok=True)

    # Copy images to respective directories
    shutil.copy(light_image_path, images_dir / Path(light_image_path).name)
    if dark_image_path:
        shutil.copy(dark_image_path, image_dark_dir / Path(dark_image_path).name)

    # Create metadata.json
    name, email = get_git_config()
    metadata = {
        "KPlugin": {
            "Authors": [{"Email": email, "Name": name, "Name[es]": name}],
            "Id": wallpaper_name.lower().replace(" ", "-"),
            "License": "GPLv3",
            "Name": wallpaper_name,
            "Name[es]": wallpaper_name,
            "Description": f"Wallpaper {wallpaper_name}",
            "Description[es]": f"Fondo de pantalla {wallpaper_name}",
        }
    }

    metadata_path = wallpaper_dir / "metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Estructura de carpetas creada en '{wallpaper_dir}'")

    return wallpaper_dir


def set_wallpaper_and_screenshot(wallpaper_dir, go_to_desktop=False):
    if go_to_desktop:
        pyautogui.hotkey("winleft", "d")

    contents_dir = wallpaper_dir / "contents"
    images_dir = contents_dir / "images"
    image_dark_dir = contents_dir / "image_dark"
    screenshot_name = "screenshot.png"

    screenshots = []

    # Verificar existencia de imagen light
    light_images = list(images_dir.glob("*"))
    if not light_images:
        print(f"No se encontró imagen light en '{wallpaper_dir.name}'.")
        return False

    # Establecer wallpaper light
    light_wallpaper = str(light_images[0])
    subprocess.run(["plasma-apply-wallpaperimage", light_wallpaper], check=True)
    print("Wallpaper light establecido correctamente.")

    time.sleep(3)
    # Tomar captura de pantalla del wallpaper light
    light_screenshot = contents_dir / "light_screenshot.png"
    subprocess.run(
        [
            "spectacle",
            "-b",
            "-n",
            "-f",
            "-e",
            "--output",
            str(light_screenshot),
        ],
        check=True,
    )

    print(f"Captura del wallpaper light guardada!")
    screenshots.append(light_screenshot)

    # Verificar existencia de imagen dark
    dark_images = list(image_dark_dir.glob("*"))
    if dark_images:
        # Establecer wallpaper dark
        dark_wallpaper = str(dark_images[0])
        subprocess.run(["plasma-apply-wallpaperimage", dark_wallpaper], check=True)
        print("Wallpaper dark establecido correctamente.")

        time.sleep(3)
        # Tomar captura de pantalla del wallpaper dark
        dark_screenshot = contents_dir / "dark_screenshot.png"
        subprocess.run(
            [
                "spectacle",
                "-b",
                "-n",
                "-f",
                "-e",
                "--output",
                str(dark_screenshot),
            ],
            check=True,
        )

        print(f"Captura del wallpaper dark guardada!")
        screenshots.append(dark_screenshot)

        # Combinar capturas de pantalla
        combined_screenshot = contents_dir / screenshot_name
        combine_screenshots(light_screenshot, dark_screenshot, combined_screenshot)
        print(f"Captura combinada guardada en {combined_screenshot}")

        # Eliminar capturas individuales
        light_screenshot.unlink()
        dark_screenshot.unlink()
    else:
        # Renombrar la captura light a screenshot.png
        final_screenshot = contents_dir / screenshot_name
        light_screenshot.rename(final_screenshot)
        print(f"Captura guardada en {final_screenshot}")

    if go_to_desktop:
        pyautogui.hotkey("winleft", "d")

    return True


def combine_screenshots(light_image_path, dark_image_path, output_path):
    # Abrir imágenes
    light_image = Image.open(light_image_path)
    dark_image = Image.open(dark_image_path)

    # Asegurarse de que las imágenes tengan el mismo tamaño
    width, height = light_image.size
    dark_image = dark_image.resize((width, height))

    # Crear nueva imagen con el mismo tamaño
    combined_image = Image.new("RGB", (width, height))

    # Crear una máscara para la transición diagonal
    mask = Image.new("L", (width, height))
    draw = ImageDraw.Draw(mask)
    draw.polygon([(0, 0), (width, 0), (0, height)], fill=255)

    # Combinar las imágenes usando la máscara
    combined_image = Image.composite(light_image, dark_image, mask)

    # Guardar imagen combinada
    combined_image.save(output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera capturas de pantalla de wallpapers"
    )
    parser.add_argument("name", help="Nombre del wallpaper")
    parser.add_argument("light_image", help="Ruta de la imagen light")
    parser.add_argument(
        "dark_image", nargs="?", help="Ruta de la imagen dark (opcional)"
    )
    args = parser.parse_args()

    wallpapers_dir = Path(__file__).resolve().parent

    print(
        "Se genera screenshot. Por favor, no muevas el mouse ni toques el teclado.\n\n"
    )
    time.sleep(2)

    pyautogui.hotkey("winleft", "d")

    wallpaper_dir = create_wallpaper_structure(
        args.name, args.light_image, args.dark_image
    )

    set_wallpaper_and_screenshot(wallpaper_dir)

    pyautogui.alert(
        text="¡Proceso completado!",
        title="Generación",
        button="OK",
    )

    # Import and validate the newly created wallpaper
    from ValidateWallpapers import validate_wallpaper

    validation_report = validate_wallpaper(wallpaper_dir)

    if validation_report["errors"]:
        print("\nErrores encontrados en la validación:")
        for error in validation_report["errors"]:
            print(f"  - {error}")
    if validation_report["warnings"]:
        print("\nAdvertencias encontradas en la validación:")
        for warning in validation_report["warnings"]:
            print(f"  - {warning}")
