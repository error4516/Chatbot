import os
import uvicorn
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq


# ✅ Load environment variables from .env file
load_dotenv()

# ✅ Secure API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

if not GROQ_API_KEY:
    raise ValueError("❌ Missing Groq API Key. Set it in an .env file.")

# ✅ Initialize FastAPI app
app = FastAPI()

# ✅ Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Create necessary directories
UPLOAD_FOLDER = "./document_store"
CHROMA_DB_DIR = "./chroma_db"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CHROMA_DB_DIR, exist_ok=True)

# ✅ Initialize embedding model & vector database
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)

# ✅ Setup Retrieval-based QA Chain
qa_chain = RetrievalQA.from_chain_type(
    llm=ChatGroq(model_name="mixtral-8x7b-32768", groq_api_key=GROQ_API_KEY),
    retriever=vector_db.as_retriever(),
)

# ✅ Root endpoint
@app.get("/")
def read_root():
    return {"message": "🚀 Welcome to the chatbot backend!"}

# ✅ Updated Search Query Endpoint
@app.get("/search/")
async def search_query(query: str):
    try:
        # Use the new `invoke` method instead of `get_relevant_documents`
        result = qa_chain.invoke({"query": query})
        retrieved_docs = vector_db.similarity_search(query)

        print("🔍 Retrieved Chunks:")
        for doc in retrieved_docs:
            print(f"\n---\n{doc.page_content}\n---")

        return {
            "retrieved_chunks": [doc.page_content for doc in retrieved_docs],
            "answer": result['result']
        }

    except Exception as e:
        print(f"❌ Search Error: {str(e)}")
        return JSONResponse(content={"error": f"Error processing your request: {str(e)}"}, status_code=500)

# ✅ Optional: Dummy /files/ endpoint to prevent 404 errors
@app.get("/files/")
async def list_files():
    try:
        files = os.listdir(UPLOAD_FOLDER)
        return {"uploaded_files": files}
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save file to UPLOAD_FOLDER
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Load document into ChromaDB
        if file.filename.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file.filename.endswith(".txt"):
            loader = TextLoader(file_path)
        else:
            return JSONResponse(
                content={"error": "Unsupported file format. Upload a .pdf or .txt file."},
                status_code=400
            )

        # Split and store documents
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        chunks = text_splitter.split_documents(documents)
        
        # ✅ Correct way to persist ChromaDB
        vector_db.add_documents(chunks)
        vector_db.get().persist()  # ✅ Fix: Use `.get().persist()`

        return {"message": "File uploaded and indexed successfully!", "filename": file.filename}

    except Exception as e:
        print(f"❌ Upload Error: {str(e)}")
        traceback.print_exc()
        return JSONResponse(content={"error": f"File upload failed: {str(e)}"}, status_code=500)


# ✅ Search query in indexed documents
@app.get("/search/")
async def search_query(query: str):
    try:
        retrieved_docs = qa_chain.retriever.get_relevant_documents(query)

        print("🔍 Retrieved Chunks:")
        for doc in retrieved_docs:
            print(f"\n---\n{doc.page_content}\n---")

        result = qa_chain.run(query)
        return {"retrieved_chunks": [doc.page_content for doc in retrieved_docs], "answer": result}

    except Exception as e:
        print(f"❌ Search Error: {str(e)}")
        traceback.print_exc()
        return JSONResponse(content={"error": f"Error processing your request: {str(e)}"}, status_code=500)

# ✅ Start Uvicorn server properly
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
