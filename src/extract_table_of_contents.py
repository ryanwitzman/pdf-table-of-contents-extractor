import tempfile
import uuid
from os.path import join
from pathlib import Path
from typing import AnyStr
from paragraph_extraction_trainer.PdfSegment import PdfSegment
from pdf_features.PdfFeatures import PdfFeatures
from pdf_features.Rectangle import Rectangle
from pdf_token_type_labels.TokenType import TokenType
from TOCExtractor import TOCExtractor
from configuration import service_logger, title_types, skip_types
from toc.PdfSegmentation import PdfSegmentation
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# Azure credentials and endpoint
AZURE_ENDPOINT = process.env.AZURE_ENDPOINT
AZURE_KEY = process.env.AZURE_KEY

def get_file_path(file_name, extension):
    return join(tempfile.gettempdir(), file_name + "." + extension)


def pdf_content_to_pdf_path(file_content):
    file_id = str(uuid.uuid1())

    pdf_path = Path(get_file_path(file_id, "pdf"))
    pdf_path.write_bytes(file_content)

    return pdf_path


def skip_name_of_the_document(pdf_segments: list[PdfSegment], title_segments: list[PdfSegment]):
    segments_to_remove = []
    last_segment = None
    for segment in pdf_segments:
        if segment.segment_type not in skip_types:
            break
        if segment.segment_type == TokenType.PAGE_HEADER or segment.segment_type == TokenType.PICTURE:
            continue
        if not last_segment:
            last_segment = segment
        else:
            if segment.bounding_box.right < last_segment.bounding_box.left + last_segment.bounding_box.width * 0.66:
                break
            last_segment = segment
        if segment.segment_type in title_types:
            segments_to_remove.append(segment)
    for segment in segments_to_remove:
        title_segments.remove(segment)


def get_pdf_segments_from_segment_boxes(pdf_features: PdfFeatures, segment_boxes: list[dict]) -> list[PdfSegment]:
    pdf_segments: list[PdfSegment] = []
    for segment_box in segment_boxes:
        left, top, width, height = segment_box["left"], segment_box["top"], segment_box["width"], segment_box["height"]
        bounding_box = Rectangle.from_width_height(left, top, width, height)
        segment_type = TokenType.from_text(segment_box["type"])
        pdf_name = pdf_features.file_name
        segment = PdfSegment(segment_box["page_number"], bounding_box, segment_box["text"], segment_type, pdf_name)
        pdf_segments.append(segment)
    return pdf_segments


def extract_text_with_azure(file_path):
    client = DocumentAnalysisClient(endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY))
    with open(file_path, "rb") as pdf_file:
        poller = client.begin_analyze_document("prebuilt-document", document=pdf_file)
        result = poller.result()

    text_segments = []
    for page in result.pages:
        for line in page.lines:
            text_segments.append({
                "page_number": page.page_number,
                "left": line.bounding_box[0].x,
                "top": line.bounding_box[0].y,
                "width": line.bounding_box[2].x - line.bounding_box[0].x,
                "height": line.bounding_box[2].y - line.bounding_box[0].y,
                "text": line.content,
                "type": "TEXT"
            })

    return text_segments


def extract_table_of_contents(file: AnyStr, segment_boxes: list[dict], skip_document_name=False):
    service_logger.info("Getting TOC")
    pdf_path = pdf_content_to_pdf_path(file)
    pdf_features: PdfFeatures = PdfFeatures.from_pdf_path(pdf_path)
    pdf_segments: list[PdfSegment] = get_pdf_segments_from_segment_boxes(pdf_features, segment_boxes)

    # If no text is found in initial extraction, use Azure OCR
    if not pdf_segments:
        service_logger.info("No text found, using Azure OCR")
        ocr_segments = extract_text_with_azure(pdf_path)
        pdf_segments = get_pdf_segments_from_segment_boxes(pdf_features, ocr_segments)

    title_segments = [segment for segment in pdf_segments if segment.segment_type in title_types]
    if skip_document_name:
        skip_name_of_the_document(pdf_segments, title_segments)
    pdf_segmentation: PdfSegmentation = PdfSegmentation(pdf_features, title_segments)
    toc_instance: TOCExtractor = TOCExtractor(pdf_segmentation)
    return toc_instance.to_dict()
