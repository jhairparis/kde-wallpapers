import json
import re
from pathlib import Path
import argparse


def snake_case(name):
    # Update to handle CamelCase to snake_case conversion
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1)
    return re.sub(r"[\W|_]+", "_", s2).lower()


def fix_metadata_json(wallpaper_dir, expected_id):
    metadata_file = wallpaper_dir / "metadata.json"
    default_metadata = {
        "KPlugin": {
            "Id": expected_id,
            "Name": wallpaper_dir.name,
            "Authors": [],
            # ...add other required fields...
        }
    }
    with open(metadata_file, "w") as f:
        json.dump(default_metadata, f, indent=4)
    print(f"metadata.json ha sido creado en '{wallpaper_dir.name}'.")


def fix_authors(kplugin, metadata_file, wallpaper_dir, author_idx=None):
    if author_idx is None:
        print(f"\nAgregando información del autor en '{wallpaper_dir.name}'...")
    else:
        print(
            f"\nAgregando campos faltantes para el autor {author_idx+1} en '{wallpaper_dir.name}'..."
        )
    name = input("Ingrese el nombre del autor: ")
    email = input("Ingrese el email del autor: ")
    name_es = input("Ingrese el nombre del autor en español: ")
    author_info = {"Name": name, "Email": email, "Name[es]": name_es}
    if author_idx is None:
        kplugin["Authors"] = [author_info]
    else:
        kplugin["Authors"][author_idx].update(author_info)
    with open(metadata_file, "w") as f:
        json.dump({"KPlugin": kplugin}, f, indent=4)
    print(f"Autores actualizados en metadata.json de '{wallpaper_dir.name}'.")


def fix_id(kplugin, expected_id, metadata_file, wallpaper_dir):
    kplugin["Id"] = expected_id
    with open(metadata_file, "w") as f:
        json.dump({"KPlugin": kplugin}, f, indent=4)
    print(f"Id ha sido corregido en metadata.json de '{wallpaper_dir.name}'.")


def fix_images_directory(images_dir, wallpaper_name):
    images = [f for f in images_dir.iterdir() if f.is_file()]
    if len(images) > 1:
        print(
            f"Múltiples imágenes encontradas en contents/images de '{wallpaper_name}':"
        )
        for idx, image in enumerate(images):
            print(f"{idx + 1}: {image.name}")
        choice = (
            int(input("Seleccione el número de la imagen que desea conservar: ")) - 1
        )
        for idx, image in enumerate(images):
            if idx != choice:
                image.unlink()
        print("Las imágenes sobrantes han sido eliminadas.")
    elif not images:
        print(f"No se encontraron imágenes en contents/images de '{wallpaper_name}'.")


def validate_wallpaper(wallpaper_dir):
    report = {"folder": wallpaper_dir.name, "errors": [], "warnings": []}
    metadata_file = wallpaper_dir / "metadata.json"
    contents_dir = wallpaper_dir / "contents"
    expected_id = f"com.jhairparis.{snake_case(wallpaper_dir.name)}"

    # Add screenshot validation
    screenshot_file = contents_dir / "screenshot.png"
    if not screenshot_file.exists():
        print(
            f"\nNo se encontró screenshot.png en contents/ de '{wallpaper_dir.name}'."
        )
        choice = input(
            f"¿Desea generar el screenshot para '{wallpaper_dir.name}'? (s/n): "
        )
        if choice.lower() == "s":
            from Generate import set_wallpaper_and_screenshot

            if set_wallpaper_and_screenshot(wallpaper_dir, True):
                print(f"Screenshot generado exitosamente para '{wallpaper_dir.name}'.")
            else:
                report["errors"].append("No se pudo generar screenshot.png")
        else:
            report["errors"].append("screenshot.png no encontrado en contents/")

    expected_id = f"com.jhairparis.{snake_case(wallpaper_dir.name)}"

    # Validate metadata.json exists
    if not metadata_file.exists():
        print(f"\nNo se encontró metadata.json en '{wallpaper_dir.name}'.")
        choice = input(
            f"¿Desea crear un metadata.json predeterminado para '{wallpaper_dir.name}'? (s/n): "
        )
        if choice.lower() == "s":
            fix_metadata_json(wallpaper_dir, expected_id)
        else:
            report["errors"].append("metadata.json no encontrado")
            return report

    # Load metadata.json
    try:
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
    except Exception as e:
        report["errors"].append(f"Error al leer metadata.json: {e}")
        return report

    kplugin = metadata.get("KPlugin", {})
    if not kplugin:
        report["errors"].append("Sección KPlugin faltante en metadata.json")
        return report

    # Validar campos requeridos en KPlugin
    required_fields = ["License", "Name", "Name[es]", "Description", "Description[es]"]
    missing_fields = [field for field in required_fields if field not in kplugin]
    if missing_fields:
        print(
            f"\nEn '{wallpaper_dir.name}' faltan los siguientes campos en metadata.json: {', '.join(missing_fields)}."
        )
        choice = input(f"¿Desea agregarlos en '{wallpaper_dir.name}'? (s/n): ")
        if choice.lower() == "s":
            for field in missing_fields:
                value = input(f"Ingrese el valor para {field}: ")
                kplugin[field] = value
            with open(metadata_file, "w") as f:
                json.dump({"KPlugin": kplugin}, f, indent=4)
            print(
                f"Los campos faltantes han sido agregados a metadata.json de '{wallpaper_dir.name}'."
            )
        else:
            report["errors"].append(f"Faltan los campos: {', '.join(missing_fields)}")

    # Check for at least one author
    authors = kplugin.get("Authors", [])
    if not authors:
        print(f"\nNo se encontraron autores en '{wallpaper_dir.name}'.")
        choice = input(f"¿Desea agregar un autor en '{wallpaper_dir.name}'? (s/n): ")
        if choice.lower() == "s":
            fix_authors(kplugin, metadata_file, wallpaper_dir)
        else:
            report["errors"].append("Se requiere al menos un autor en metadata")
    else:
        for idx, author in enumerate(authors):
            required_author_fields = ["Email", "Name", "Name[es]"]
            missing_author_fields = [
                field for field in required_author_fields if field not in author
            ]
            if missing_author_fields:
                print(
                    f"\nEn '{wallpaper_dir.name}', el autor {idx+1} carece de los siguientes campos: {', '.join(missing_author_fields)}."
                )
                choice = input(
                    f"¿Desea agregarlos para el autor {idx+1} en '{wallpaper_dir.name}'? (s/n): "
                )
                if choice.lower() == "s":
                    fix_authors(kplugin, metadata_file, wallpaper_dir, idx)
                else:
                    report["errors"].append(
                        f"El autor {idx+1} carece de los campos: {', '.join(missing_author_fields)}"
                    )

    # Validate Id format
    actual_id = kplugin.get("Id", "")
    if actual_id != expected_id:
        print(
            f"\nId incorrecto en '{wallpaper_dir.name}'. Se esperaba '{expected_id}', se encontró '{actual_id}'."
        )
        choice = input(f"¿Desea corregir el Id en '{wallpaper_dir.name}'? (s/n): ")
        if choice.lower() == "s":
            fix_id(kplugin, expected_id, metadata_file, wallpaper_dir)
        else:
            report["errors"].append(
                f"Id debería ser '{expected_id}', se encontró '{actual_id}'"
            )

    contents_dir = wallpaper_dir / "contents"
    images_dir = contents_dir / "images"
    image_dark_dir = contents_dir / "image_dark"

    # Validate exactly one image in contents/images
    if images_dir.exists():
        images = [f for f in images_dir.iterdir() if f.is_file()]
        if len(images) != 1:
            print(
                f"\nDebe haber exactamente una imagen en contents/images de '{wallpaper_dir.name}'."
            )
            choice = input(
                f"¿Desea corregir el directorio de imágenes en '{wallpaper_dir.name}'? (s/n): "
            )
            if choice.lower() == "s":
                fix_images_directory(images_dir, wallpaper_dir.name)
            else:
                report["errors"].append(
                    "Número incorrecto de imágenes en contents/images"
                )
    else:
        report["errors"].append("Directorio contents/images no encontrado")

    # Check for image in contents/image_dark
    if image_dark_dir.exists():
        dark_images = [f for f in image_dark_dir.iterdir() if f.is_file()]
        if not dark_images:
            report["warnings"].append("No se encontró imagen en contents/image_dark")
    else:
        report["warnings"].append("Directorio contents/image_dark no encontrado")

    return report


def main():
    # Add argument parsing
    parser = argparse.ArgumentParser(description="Validar wallpapers")
    parser.add_argument(
        "folder", nargs="?", help="Carpeta específica de wallpaper a validar"
    )
    args = parser.parse_args()

    wallpapers_dir = Path(__file__).resolve().parent
    reports = []

    if args.folder:
        # Validate only the specified folder
        wallpaper_dir = wallpapers_dir / args.folder
        if wallpaper_dir.is_dir():
            report = validate_wallpaper(wallpaper_dir)
            reports.append(report)
        else:
            print(f"La carpeta '{args.folder}' no existe.")
            return
    else:
        # Validate all folders
        for wallpaper_dir in wallpapers_dir.iterdir():
            if wallpaper_dir.is_dir():
                report = validate_wallpaper(wallpaper_dir)
                reports.append(report)

    # Generate the general report
    print("\nReporte de Validación:")
    for report in reports:
        print(f"\nCarpeta: {report['folder']}")
        if report["errors"]:
            print("Errores:")
            for error in report["errors"]:
                print(f"  - {error}")
        else:
            print("Todas las validaciones pasaron")
        if report["warnings"]:
            print("Advertencias:")
            for warning in report["warnings"]:
                print(f"  - {warning}")


if __name__ == "__main__":
    main()
