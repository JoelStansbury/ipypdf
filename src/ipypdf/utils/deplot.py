from transformers import Pix2StructProcessor, Pix2StructForConditionalGeneration, pipeline

detector = pipeline(model="openai/clip-vit-large-patch14", task="zero-shot-image-classification")
processor = Pix2StructProcessor.from_pretrained('google/deplot')
model = Pix2StructForConditionalGeneration.from_pretrained('google/deplot')

def try_to_parse_chart_data(image, force=False):
    image_type_predictions = {x["label"]: x["score"] for x in detector(image, candidate_labels=["chart", "other"])}
    if force or image_type_predictions["chart"] > 0.5:
        print("It looks like a chart... passing image to DePlot. This may take ~5 minutes")
        inputs = processor(images=image, text="Generate underlying data table of the figure below:", return_tensors="pt")
        predictions = model.generate(**inputs, max_new_tokens=512)
        s = processor.decode(predictions[0], skip_special_tokens=True)
        table = [[v.strip() for v in x.split("|")] for x in s.split("<0x0A>")]
        print(s)
        return {
            "raw_table_string": s,
            "table": table
        }
    else:
        print("Image does not appear to be a chart")
        return {}