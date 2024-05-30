import requests
from fastapi import FastAPI, HTTPException, UploadFile, File
from extract_table_of_contents import extract_table_of_contents
from configuration import service_logger

app = FastAPI()


@app.post("/")
async def get_toc(file: UploadFile = File(...)):
    try:
        service_logger.info(f"Processing file: {file.filename}")
        file_content = file.file.read()
        response = requests.post("http://pdf-layout-analysis:5060/", files={"file": (file.filename, file_content, file.content_type)})
        return extract_table_of_contents(file_content, response.json())
    except requests.RequestException as e:
        raise HTTPException(status_code=422, detail=str(e))