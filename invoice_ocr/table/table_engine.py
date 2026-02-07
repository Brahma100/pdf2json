from paddleocr import PPStructure

table_engine = PPStructure(
    show_log=False,
    use_gpu=False
)

def extract_tables(image):
    return table_engine(image)
