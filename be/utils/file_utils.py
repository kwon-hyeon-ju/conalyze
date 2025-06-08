from pdf2image import convert_from_path

def pdf_to_images(pdf_path):
    images = convert_from_path(pdf_path)  
    image_paths = []
    for i, img in enumerate(images):
        path = f"page_{i}.jpg"
        img.save(path, 'JPEG')
        image_paths.append(path)
    return image_paths
