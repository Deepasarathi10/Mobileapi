


import json
import logging
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, status, Query
from WhatsappConfig.utils import get_whatsapp_config_collection 
from WhatsappConfig.models import WhatsappConfig, WhatsappConfigPost
from WhatsApp.utils import get_whatsApp_collection
import requests

router = APIRouter()

# Constants
# MAX_QUEUE_SIZE = 0  # Maximum number of configs to maintain in FIFO queue
WHATSAPP_API_URL = 'https://backend.askeva.io/v1/message/send-message?token=226b3bc6338f9de4107cc93016924fb2868113776165b8d4b9a76914930e2fa2e47ff2906d87e0281121e425dccf62d84a6a82303c99beb2c24d0f9da7a46c1e32af25b2e74b7e42a7d17ce834c474aeb9b4abecdf454ade5fcd7519b8dd2e3893e0ac008bf50aa0d2ddc59737e381d4166d7d1e45af5cb285d388959efdc897c43af27799a56ea571830eca7cb8d5f08cf4284b28dff365fb85a2ad9d645ee0aaf8a86e8d6103150f29361e0f4556ba02cbf0149bacd06ad35fbe51d0ba630533cf73a51476c02eccc3845d13506638'
ADMIN_MOBILE_NUMBER = "9360556923" 

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Helper function to convert MongoDB document to Pydantic model
def document_to_whatsapp_config(document):
    if not document:
        return None
    document["whatsappConfigId"] = str(document["_id"])
    del document["_id"]
    return WhatsappConfig(**document)

def update_module_status(config_id: str):
    """Helper function to update the module status based on submodule statuses"""
    config = get_whatsapp_config_collection().find_one({"_id": ObjectId(config_id)})
    if not config:
        return
    
    submodules = config.get("subModules", [])
    if not submodules:
        return
    
    # Check if any submodule is active
    any_submodule_active = any(submodule.get("status", False) for submodule in submodules)
    
    # Update the module status
    get_whatsapp_config_collection().update_one(
        {"_id": ObjectId(config_id)},
        {"$set": {
            "status": any_submodule_active,
            "updatedDate": datetime.utcnow()
        }}
    )

def enforce_fifo_queue():
    """Ensure the collection doesn't exceed MAX_QUEUE_SIZE by removing oldest items"""
    current_count = get_whatsapp_config_collection().count_documents({})
    


def send_whatsapp_message(phone_number: str, message_data: dict):
    """Helper function to send WhatsApp message with error handling"""
    try:
        logger.info(f"Sending WhatsApp to: 91{phone_number}")
        logger.debug(f"Payload: {json.dumps(message_data, indent=2)}")

        response = requests.post(
            WHATSAPP_API_URL,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json=message_data,
            timeout=15
        )
        
        if response.status_code == 200:
            logger.info(f"Successfully sent WhatsApp to {phone_number}")
            return True
        else:
            error_msg = response.json().get('message', 'No error message returned') if response.content else 'No content'
            logger.error(
                f"WhatsApp API failed for {phone_number}. "
                f"Status: {response.status_code}. Error: {error_msg}"
            )
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed for {phone_number}: {str(e)}")
        return False
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON response for {phone_number}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error for {phone_number}: {str(e)}")
        return False

## Get All
@router.get("/", response_model=List[WhatsappConfig])
async def get_all_whatsapp_configs(
    newest_first: bool = False
):
    try:
        sort_order = -1 if newest_first else 1
        query = get_whatsapp_config_collection().find().sort("createdDate", sort_order)
        
            
        configs = list(query)
        return [document_to_whatsapp_config(config) for config in configs]
    except Exception as e:
        logging.error(f"Error fetching WhatsApp configs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED)
async def create_whatsapp_config(config_data: WhatsappConfigPost):
    try:
        # Ensure we don't exceed queue size
        enforce_fifo_queue()

        new_config = config_data.dict()

        # Set defaults
        new_config["status"] = False
        new_config["createdDate"] = datetime.utcnow()
        new_config["whatsappSent"] = False  # Track WhatsApp message status

        # Process submodules if they exist
        if "subModules" in new_config and new_config["subModules"]:
            for submodule in new_config["subModules"]:
                submodule["subModuleId"] = str(ObjectId())
                submodule["status"] = False
                submodule["createdDate"] = datetime.utcnow()
                submodule["enableMessage"] = []  # Initialize empty list for roles

        result = get_whatsapp_config_collection().insert_one(new_config)

        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save WhatsApp config"
            )

        # Prepare WhatsApp message data
        config_id_str = str(result.inserted_id)
        
        # Use static phone number
        phone_number = ''.join(filter(str.isdigit, ADMIN_MOBILE_NUMBER))
        if len(phone_number) != 10:
            logger.warning(f"Invalid ADMIN mobile number format: {ADMIN_MOBILE_NUMBER}")
            # Update WhatsApp status to false if number is invalid
            get_whatsapp_config_collection().update_one(
                {"_id": result.inserted_id},
                {"$set": {"whatsappSent": False}}
            )
            return config_id_str

        # Prepare WhatsApp message template
        whatsapp_message = {
            "to": f"91{phone_number}",
            "type": "template",
            "template": {
                "language": {"policy": "deterministic", "code": "en"},
                "name": "whatsapp_test",
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "image",
                                "image": {"link": "https://yenerp.com/share/offer.jpg"}
                            }
                        ]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "WhatsApp Config Created"},
                            {"type": "text", "text": f"Config ID: {config_id_str}"},
                            {"type": "text", "text": f"Status: {new_config['status']}"}
                        ]
                    }
                ]
            }
        }

        # Send message to the static number
        message_sent = send_whatsapp_message(phone_number, whatsapp_message)

        # Update the document with WhatsApp status
        get_whatsapp_config_collection().update_one(
            {"_id": result.inserted_id},
            {"$set": {"whatsappSent": message_sent}}
        )

        return config_id_str

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing request"
        )

## Get By ID
@router.get("/{config_id}", response_model=WhatsappConfig)
async def get_whatsapp_config_by_id(config_id: str):
    try:
        config = get_whatsapp_config_collection().find_one({"_id": ObjectId(config_id)})
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        return document_to_whatsapp_config(config)
    except Exception as e:
        logging.error(f"Error fetching config {config_id}: {e}")
        raise HTTPException(status_code=400, detail="Invalid config ID")

## Patch
@router.patch("/{config_id}", response_model=WhatsappConfig)
async def update_whatsapp_config(config_id: str, config_patch: WhatsappConfigPost):
    try:
        existing_config = get_whatsapp_config_collection().find_one({"_id": ObjectId(config_id)})
        if not existing_config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        update_data = config_patch.dict(exclude_unset=True)
        update_data["updatedDate"] = datetime.utcnow()
        
        # Handle submodule updates
        if "subModules" in update_data and update_data["subModules"]:
            for submodule in update_data["subModules"]:
                if "subModuleId" not in submodule or not submodule["subModuleId"]:
                    submodule["subModuleId"] = str(ObjectId())
                    submodule["createdDate"] = datetime.utcnow()
                    submodule["enableMessage"] = []
                    submodule["status"] = False
                    submodule["updatedDate"] = datetime.utcnow()
        
        result = get_whatsapp_config_collection().update_one(
            {"_id": ObjectId(config_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Update failed")
        
        # Update module status based on submodules
        update_module_status(config_id)
        
        updated_config = get_whatsapp_config_collection().find_one({"_id": ObjectId(config_id)})
        return document_to_whatsapp_config(updated_config)
    except Exception as e:
        logging.error(f"Error updating config {config_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

## Get By Module Name 
@router.get("/module/{module_name}", response_model=WhatsappConfig)
async def get_whatsapp_config_by_module(module_name: str):
    try:
        config = get_whatsapp_config_collection().find_one({"module": module_name})
        if not config:
            raise HTTPException(status_code=404, detail=f"Config for module '{module_name}' not found")
        return document_to_whatsapp_config(config)
    except Exception as e:
        logging.error(f"Error fetching config for module {module_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.get("/oldest", response_model=WhatsappConfig)
async def get_oldest_config():
    """Get the oldest config in the queue (FIFO peek)"""
    try:
        oldest_config = get_whatsapp_config_collection().find_one(
            {}, 
            sort=[("createdDate", 1)]  # Oldest first
        )
        if not oldest_config:
            raise HTTPException(status_code=404, detail="No configs found")
        return document_to_whatsapp_config(oldest_config)
    except Exception as e:
        logging.error(f"Error fetching oldest WhatsApp config: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    

@router.patch("/{config_id}/submodule/{submodule_id}/toggle-role", response_model=WhatsappConfig)
async def toggle_whatsAppRole_permission(
    config_id: str,
    submodule_id: str,
    whatsAppRollName: str,   
    action: str  # 'add' or 'remove'
):
    try:
        # Find the config
        config = get_whatsapp_config_collection().find_one({"_id": ObjectId(config_id)})
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        # Find the submodule
        submodule_index = None
        submodule = None
        for i, sm in enumerate(config.get("subModules", [])):
            if sm.get("subModuleId") == submodule_id:
                submodule_index = i
                submodule = sm
                break
        
        if not submodule:
            raise HTTPException(status_code=404, detail="Submodule not found")
        
        # Initialize enableMessage if not exists
        if "enableMessage" not in submodule:
            submodule["enableMessage"] = []
        
        # Update the role list and determine new submodule status
        new_submodule_status = submodule.get("status", False)
        
        if action == "add":
            if whatsAppRollName not in submodule["enableMessage"]:
                submodule["enableMessage"].append(whatsAppRollName)
                new_submodule_status = True
        elif action == "remove":
            if whatsAppRollName in submodule["enableMessage"]:
                submodule["enableMessage"].remove(whatsAppRollName)
                if not submodule["enableMessage"]:
                    new_submodule_status = False
        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'add' or 'remove'")

        # Update the document in MongoDB
        update_path = f"subModules.{submodule_index}"
        result = get_whatsapp_config_collection().update_one(
            {"_id": ObjectId(config_id)},
            {
                "$set": {
                    f"{update_path}.enableMessage": submodule["enableMessage"],
                    f"{update_path}.status": new_submodule_status,
                    "updatedDate": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=500, detail="Failed to update role permission")
        
        # Update the parent module status based on submodule statuses
        update_module_status(config_id)
        
        updated_config = get_whatsapp_config_collection().find_one({"_id": ObjectId(config_id)})
        return document_to_whatsapp_config(updated_config)
    except Exception as e:
        logging.error(f"Error toggling role permission: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
    


@router.post("/{config_id}/submodule/{submodule_id}/send-message", response_model=dict)
async def send_role_message(
    config_id: str,
    submodule_id: str,
    whatsAppRollName: str
):
    try:
        # Find the config
        config = get_whatsapp_config_collection().find_one({"_id": ObjectId(config_id)})
        if not config:
            raise HTTPException(status_code=404, detail="Config not found")
        
        # Find the submodule
        submodule = None
        for sm in config.get("subModules", []):
            if sm.get("subModuleId") == submodule_id:
                submodule = sm
                break
        
        if not submodule:
            raise HTTPException(status_code=404, detail="Submodule not found")
        
        # Find phone number associated with the role (assuming roles are stored in WhatsApp collection)
        role_record = get_whatsApp_collection().find_one({"whatsAppRollName": whatsAppRollName})
        if not role_record or "mobileNumber" not in role_record:
            raise HTTPException(status_code=404, detail=f"No phone number found for role {whatsAppRollName}")
        
        phone_number = role_record["mobileNumber"]
        clean_number = ''.join(filter(str.isdigit, str(phone_number)))
        if len(clean_number) != 10:
            raise HTTPException(status_code=400, detail=f"Invalid phone number format: {phone_number}")
        
        # Prepare WhatsApp message
        whatsapp_message = {
            "to": f"91{clean_number}",
            "type": "template",
            "template": {
                "language": {"policy": "deterministic", "code": "en"},
                "name": "whatsapp_test",
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "image",
                                "image": {"link": "https://yenerp.com/share/offer.jpg"}
                            }
                        ]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": "Submodule Permission Updated"},
                            {"type": "text", "text": f"Submodule: {submodule['subModuleName']}"},
                            {"type": "text", "text": f"Role: {whatsAppRollName}"}
                        ]
                    }
                ]
            }
        }
        
        # Send the message
        if send_whatsapp_message(clean_number, whatsapp_message):
            return {"message": f"WhatsApp message sent to role {whatsAppRollName}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send WhatsApp message")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending message for role {whatsAppRollName}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")