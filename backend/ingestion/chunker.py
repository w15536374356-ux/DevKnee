from  langchain_text_splitters import  MarkdownHeaderTextSplitter,RecursiveCharacterTextSplitter

MAX_CHUNK_LEN=500
OVERLAP=80

def chunk_segement(segement:list[dict])->list[dict]:
    #合体
    md_lines=[]
    for sec in segement:
        if sec["type"]=="heading":
            md_lines.append("#"*sec["level"]+" "+sec["text"])
        else:
            md_lines.append(sec["text"])
    md_lines="\n".join(md_lines)

    #拆标题
    md_splitter=MarkdownHeaderTextSplitter(
        headers_to_split_on=[
            ("#","h1"),
            ("##","h2"),
            ("###","h3"),
            ("####","h4"),
        ]
    )
    md_header=md_splitter.split_text(md_lines)

    text_splitter=RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHUNK_LEN,
        overlap=OVERLAP
    )
    chunks:list[dict]=[]
    for sec in md_header:
        title="/".join(x for x in sec.metadata.values() if x) or "" #拼标题路径
        for part in text_splitter.split_text(sec.page_content):
            chunks.append({"title":title,"content":part})
    return chunks   



