import logging
import os
import time
import mimetypes
import asyncio
from concurrent.futures import ThreadPoolExecutor
from bson import ObjectId
from fastapi import APIRouter, FastAPI, File, Request, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import ffmpeg
from pymongo import MongoClient
import traceback
import re
# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
app = FastAPI(max_upload_size=1024 * 1024 * 1024 * 5)
router = APIRouter()
executor = ThreadPoolExecutor(max_workers=5)

def get_video_collection():
    try:
        client = MongoClient("mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster")
        db = client["dailyactivities"]
        # Test the connection
        db.command('ping') 
        return db['video']
    except Exception as e:
        logger.error(f"MongoDB connection error: {str(e)}")
        raise

# VIDEO_DIR = "videos"
# COMPRESSED_VIDEO_DIR = "compressed_videos"
BASE_URL = "https://yenerp.com/share/upload"
VIDEO_DIR = "/var/www/vhosts/yenerp.com/httpdocs/share/upload/videos"  # Adjust this path based on your server configuration
COMPRESSED_VIDEO_DIR = "/var/www/vhosts/yenerp.com/httpdocs/share/upload/compressed_videos"
CHUNK_SIZE = 1024 * 1024*8  # 8MB chunks
THUMBNAIL_DIR = "/var/www/vhosts/yenerp.com/httpdocs/share/upload/thumbnails"


# Ensure directories exist with proper permissions
try:
    os.makedirs(THUMBNAIL_DIR, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)
    os.makedirs(COMPRESSED_VIDEO_DIR, exist_ok=True)
    os.chmod(VIDEO_DIR, 0o755)
    os.chmod(COMPRESSED_VIDEO_DIR, 0o755)
    os.chmod(THUMBNAIL_DIR, 0o755)
    # Test write permissions
    test_file_path = os.path.join(VIDEO_DIR, "test_write")
    with open(test_file_path, "w") as f:
        f.write("test")
    os.remove(test_file_path)
except Exception as e:
    logger.error(f"Directory setup error: {str(e)}")
    raise

def get_public_url(file_path: str) -> str:
    """Convert server file path to public URL"""
    if file_path.startswith(VIDEO_DIR):
        relative_path = os.path.relpath(file_path, "/var/www/vhosts/yenerp.com/httpdocs/share/upload")
    elif file_path.startswith(COMPRESSED_VIDEO_DIR):
        relative_path = os.path.relpath(file_path, "/var/www/vhosts/yenerp.com/httpdocs/share/upload")
    else:
        relative_path = os.path.basename(file_path)
    return f"{BASE_URL}/{relative_path}"


async def save_upload_file(upload_file: UploadFile, destination: str):
    try:
        async with aiofiles.open(destination, "wb") as file_object:
            while chunk := await upload_file.read(CHUNK_SIZE):
                await file_object.write(chunk)
        os.chmod(destination, 0o644)
        return True
    except Exception as e:
        logger.error(f"File save error: {str(e)}")
        raise

async def compress_video_async(input_path: str, output_path: str, target_size_mb: float = 15.0) -> bool:
    try:
        logger.info(f"Starting compression for {input_path}")
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
            
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            lambda: compress_video(input_path, output_path, target_size_mb)
        )
        logger.info(f"Compression completed for {input_path}")
        return result
    except Exception as e:
        logger.error(f"Compression error: {str(e)}\n{traceback.format_exc()}")
        raise

def compress_video(input_path: str, output_path: str, target_size_mb: float = 15.0) -> bool:
    try:
        logger.info(f"Probing video: {input_path}")
        probe = ffmpeg.probe(input_path)
        video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        duration = float(probe['format']['duration'])
        
        target_size_bits = target_size_mb * 8 * 1024 * 1024
        target_bitrate = int((target_size_bits * 0.8) / duration)
        
        logger.info(f"Starting FFmpeg compression: {input_path}")
        stream = (
            ffmpeg
            .input(input_path)
            .output(
                output_path,
                **{
                    'c:v': 'libx264',
                    'preset': 'ultrafast',
                    'crf': 28,
                    'maxrate': f'{target_bitrate}',
                    'bufsize': f'{target_bitrate*2}',
                    'movflags': '+faststart',
                    'threads': 8
                }
            )
        )
        
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Compressed file not created: {output_path}")
            
        logger.info(f"Compression successful: {output_path}")
        return True
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error: {e.stderr.decode('utf-8') if e.stderr else str(e)}")
        raise
    except Exception as e:
        logger.error(f"Compression error: {str(e)}\n{traceback.format_exc()}")
        raise


async def generate_thumbnail(input_path: str, output_path: str, timestamp: float = 1.0):
    """
    Generate a thumbnail image for the video.
    Args:
        input_path (str): Path to the input video file.
        output_path (str): Path to save the generated thumbnail.
        timestamp (float): Time (in seconds) to extract the frame for the thumbnail.
    """
    try:
        logger.info(f"Generating thumbnail for {input_path}")
        stream = (
            ffmpeg
            .input(input_path, ss=timestamp)
            .output(output_path, vframes=1, format='image2', vcodec='mjpeg')
            .overwrite_output()
        )
        ffmpeg.run(stream, capture_stdout=True, capture_stderr=True)
        if not os.path.exists(output_path):
            raise FileNotFoundError(f"Thumbnail not created: {output_path}")
        os.chmod(output_path, 0o644)
        logger.info(f"Thumbnail generated: {output_path}")
        return True
    except ffmpeg.Error as e:
        logger.error(f"FFmpeg error while generating thumbnail: {e.stderr.decode('utf-8') if e.stderr else str(e)}")
        raise
    except Exception as e:
        logger.error(f"Thumbnail generation error: {str(e)}")
        raise


@router.post("/")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    custom_id: Optional[str] = None
):
    temp_input_path = None
    start_time = time.time()
    
    try:
        logger.info(f"Starting upload for file: {file.filename}")
        
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
            
        temp_input_path = os.path.join(VIDEO_DIR, f"temp_{file.filename}")
        
        if custom_id and not ObjectId.is_valid(custom_id):
            raise HTTPException(status_code=400, detail="Invalid custom_id format")

        await save_upload_file(file, temp_input_path)
        if not os.path.exists(temp_input_path):
            raise FileNotFoundError(f"Upload failed: {temp_input_path} not created")
        
        original_size_mb = os.path.getsize(temp_input_path) / (1024 * 1024)
        logger.info(f"Original file size: {original_size_mb:.2f} MB")
        
        base_filename = os.path.splitext(file.filename)[0]
        compressed_filename = f"{base_filename}_compressed.mp4"
        compressed_path = os.path.join(COMPRESSED_VIDEO_DIR, compressed_filename)
        thumbnail_filename = f"{base_filename}_thumbnail.jpg"
        thumbnail_path = os.path.join(THUMBNAIL_DIR, thumbnail_filename)

        # Compress and generate thumbnail in parallel
        compression_task = asyncio.create_task(
            compress_video_async(temp_input_path, compressed_path)
        )
        thumbnail_task = asyncio.create_task(
            generate_thumbnail(temp_input_path, thumbnail_path)
        )
        await asyncio.gather(compression_task, thumbnail_task)
        
        if os.path.exists(temp_input_path):
            os.remove(temp_input_path)
        
        custom_object_id = custom_id or str(ObjectId())
        video_collection = get_video_collection()

        # Insert document into MongoDB
        insert_result = video_collection.insert_one({
            "_id": custom_object_id,
            "filename": compressed_filename,
            "filepath": compressed_path,
            "thumbnail_path": thumbnail_path,
            "public_url": get_public_url(compressed_path),
            "thumbnail_url": get_public_url(thumbnail_path),
            "original_filename": file.filename
        })
        if not insert_result.inserted_id:
            raise Exception("Database insertion failed")

        elapsed_time = time.time() - start_time
        return {
            "filename": compressed_filename,
            "id": custom_object_id,
            "url": get_public_url(compressed_path),
            "thumbnail_url": get_public_url(thumbnail_path),
            "compressed": True,
            "original_size_mb": original_size_mb,
            "compressed_size_mb": os.path.getsize(compressed_path) / (1024 * 1024),
            "upload_time_seconds": round(elapsed_time, 2)
        }

    except Exception as e:
        logger.error(f"Upload error: {str(e)}\n{traceback.format_exc()}")
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
            except Exception as cleanup_error:
                logger.error(f"Cleanup error: {str(cleanup_error)}")
        raise HTTPException(status_code=500, detail=str(e))


import aiofiles

CHUNK_SIZE = 1024 * 1024  # Adjustable chunk size (1 MB by default)

async def stream_video(file_path: str, start: int, end: int):
    """  
    Asynchronously stream video content in chunks for better performance.
    """
    async with aiofiles.open(file_path, mode="rb") as video_file:
        await video_file.seek(start)
        remaining = end - start + 1
        while remaining > 0:
            chunk_size = min(CHUNK_SIZE, remaining)
            data = await video_file.read(chunk_size)
            if not data:
                break
            yield data
            remaining -= len(data)

@router.get("/{video_id}")
async def get_video(video_id: str, request: Request):
    """
    Handle video streaming requests, supporting partial content with range headers.
    """
    try:
        # Retrieve video metadata from the database
        video_document = get_video_collection().find_one({"_id": video_id})
        if not video_document:
            raise HTTPException(status_code=404, detail="Video not found")

        file_path = video_document["filepath"]
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Video file not found")

        file_size = os.path.getsize(file_path)
        range_header = request.headers.get("range")

        if range_header:
            # Parse the range header
            range_value = range_header.strip().split("=")[1]
            start, end = range_value.split("-")
            start = int(start)
            end = int(end) if end else file_size - 1

            if start >= file_size or end >= file_size:
                raise HTTPException(status_code=416, detail="Range Not Satisfiable")

            content_length = end - start + 1
            headers = {
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(content_length),
            }

            mime_type, _ = mimetypes.guess_type(file_path)
            return StreamingResponse(
                stream_video(file_path, start, end),
                media_type=mime_type or "video/mp4",
                status_code=206,
                headers=headers,
            )
        else:
            # Serve the entire video if no range is specified
            mime_type, _ = mimetypes.guess_type(file_path)
            headers = {"Content-Length": str(file_size)}
            return StreamingResponse(
                stream_video(file_path, 0, file_size - 1),
                media_type=mime_type or "video/mp4",
                headers=headers,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in video streaming: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.get("/thumbnail/{video_id}")
async def get_thumbnail(video_id: str):
    try:
        video_document = get_video_collection().find_one({"_id": video_id})

        if video_document:
            thumbnail_path = video_document["thumbnail_path"]

            if not os.path.exists(thumbnail_path):
                raise HTTPException(status_code=404, detail="Thumbnail not found")

            return StreamingResponse(open(thumbnail_path, "rb"), media_type="image/jpeg")
        else:
            raise HTTPException(status_code=404, detail="Video not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{video_id}")
async def delete_video(video_id: str):
    try:
        # Find the video document in the database
        video_document = get_video_collection().find_one({"_id": video_id})

        if video_document:
            # Retrieve file paths
            file_path = video_document["filepath"]
            thumbnail_path = video_document["thumbnail_path"]

            # Delete the video file if it exists
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted video file: {file_path}")

            # Delete the thumbnail file if it exists
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                print(f"Deleted thumbnail file: {thumbnail_path}")

            # Remove the video document from the MongoDB collection
            get_video_collection().delete_one({"_id": video_id})
            return {"detail": "Video and thumbnail deleted successfully."}
        else:
            raise HTTPException(status_code=404, detail="Video not found")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
