import importlib
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
#import SalesOrder.routes as salesorder_routes

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    docs_url="/fastapi/doc",
    redoc_url="/fastapi/redoc",
    openapi_url="/fastapi/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["*"],
)

# app.include_router(
#     salesorder_routes.router,   # if you imported the module
#     prefix="/salesorders",
#     tags=["SalesOrder"],
# )
# List of route configuration dictionaries.
# Each dictionary contains the module path (where your router is defined),
# the prefix for the routes, and tags for the OpenAPI docs.

routes_info = [
    #Core APIs
    {"module": "ItemGroup.routes", "prefix": "/fastapi/itemgroups", "tags": ["itemgroups"]},
    {"module": "Branches.routes", "prefix": "/fastapi/branches", "tags": ["branches"]},
    {"module": "itemCategory.routes", "prefix": "/fastapi/itemcategories", "tags": ["itemcategories"]},
    {"module": "itemSubcategory.routes", "prefix": "/fastapi/itemsubcategories", "tags": ["itemsubcategories"]},
    {"module": "Uom.routes", "prefix": "/fastapi/uoms", "tags": ["uoms"]},
    {"module": "Tax.routes", "prefix": "/fastapi/taxes", "tags": ["taxes"]},
    {"module": "Discount.routes", "prefix": "/fastapi/discounts", "tags": ["discounts"]},
    {"module": "items.routes", "prefix": "/fastapi/items", "tags": ["items"]},
    {"module": "addOn.routes", "prefix": "/fastapi/addons", "tags": ["addons"]},
    {"module": "OnlinePartner.routes", "prefix": "/fastapi/OnlinePartner", "tags": ["OnlinePartner"]},
    {"module": "OnlinePartnerTemplate.routes", "prefix": "/fastapi/OnlinePartnerTemplate", "tags": ["OnlinePartnerTemplate"]},
    {"module": "orderType.routes", "prefix": "/fastapi/ordertypes", "tags": ["ordertypes"]},
    {"module": "variance.routes", "prefix": "/fastapi/variances", "tags": ["variances"]},
    {"module": "Branchwiseitem.routes", "prefix": "/fastapi/branchwiseitems", "tags": ["branchwiseitems"]},
    {"module": "gst.routes", "prefix": "/fastapi/gst", "tags": ["gst"]},
    {"module": "promotionalOffer.routes", "prefix": "/fastapi/promotionaloffers", "tags": ["promotionaloffers"]},
    {"module": "attendance.routes", "prefix": "/fastapi/attendances", "tags": ["attendances"]},
    {"module": "facialRecognization.routes", "prefix": "/fastapi/facialrecognizations", "tags": ["facialrecognations"]},
    {"module": "Invoice.routes", "prefix": "/fastapi/invoices", "tags": ["invoices"]},
    {"module": "tareWight.routes", "prefix": "/fastapi/tare", "tags": ["tare"]},
    {"module": "mixBox.routes", "prefix": "/fastapi/mixbox", "tags": ["mixbox"]},
    {"module": "stickercount.routes", "prefix": "/fastapi/stickercount", "tags": ["stickercount"]},
    {"module": "stockClossing.routes", "prefix": "/fastapi/stockclosings", "tags": ["stockclosings"]},
    {"module": "Employee.routes", "prefix": "/fastapi/employees", "tags": ["employees"]},
    {"module": "itemTransfer.routes", "prefix": "/fastapi/itemtransfers", "tags": ["itemtransfers"]},
    {"module": "orders.routes", "prefix": "/fastapi/orders", "tags": ["orders"]},
    {"module": "yenqr.routes", "prefix": "/fastapi/allitems", "tags": ["allitems"]},
    {"module": "variance2.routes", "prefix": "/fastapi/variances2", "tags": ["variances2"]},
    {"module": "varianceKKD.routes", "prefix": "/fastapi/varianceskkd", "tags": ["varianceskkd"]},
    {"module": "shift.routes", "prefix": "/fastapi/shifts", "tags": ["shifts"]},
    {"module": "dayend.routes", "prefix": "/fastapi/dayends", "tags": ["dayends"]},
    {"module": "salesReturn.routes", "prefix": "/fastapi/salesreturns", "tags": ["salesreturns"]},
    {"module": "WastageEntry.routes", "prefix": "/fastapi/wastageentrys", "tags": ["wastageentrys"]},
    {"module": "productionEntrys.routes", "prefix": "/fastapi/productionentrys", "tags": ["productionentrys"]},
    {"module": "vehicles.routes", "prefix": "/fastapi/vehicles", "tags": ["vehicles"]},
    {"module": "details.routes", "prefix": "/fastapi/details", "tags": ["details"]},
    {"module": "wareHouse.routes", "prefix": "/fastapi/warehouses", "tags": ["warehouses"]},
    {"module": "dispatch.routes", "prefix": "/fastapi/dispatches", "tags": ["dispatches"]},
    {"module": "rawMaterials.routes", "prefix": "/fastapi/rawmaterials", "tags": ["rawmaterials"]},
    {"module": "bankcash.routes", "prefix": "/fastapi/bankcashes", "tags": ["bankcash"]},
    {"module": "variant.routes", "prefix": "/fastapi/kotvariants", "tags": ["kotvariants"]},
    {"module": "hold.routes", "prefix": "/fastapi/holds", "tags": ["holds"]},
    {"module": "SOHeldOrders.routes", "prefix": "/fastapi/soholds", "tags": ["So holds"]},
    {"module": "toapprove.routes", "prefix": "/fastapi/toapproves", "tags": ["SO Toapproves"]},
    {"module": "modifyOrder.routes", "prefix": "/fastapi/modifyOrders", "tags": ["modifyOrders"]},
    {"module": "SalesOrder.routes", "prefix": "/fastapi/salesorders", "tags": ["salesorders"]},
    {"module": "creditbill.routes", "prefix": "/fastapi/creditbills", "tags": ["creditbills"]},
    {"module": "kotTableStatus.routes", "prefix": "/fastapi/kottablesstatus", "tags": ["kottablesstatus"]},
    {"module": "sections.routes", "prefix": "/fastapi/sections", "tags": ["sections"]},
    {"module": "Table.routes", "prefix": "/fastapi/tables", "tags": ["tables"]},
    {"module": "deviceCode.routes", "prefix": "/fastapi/devicecode", "tags": ["devicecode"]},
    {"module": "warehouseItems.routes", "prefix": "/fastapi/warehouseitems", "tags": ["warehouseitems"]},
    {"module": "login.routes", "prefix": "/fastapi/logins", "tags": ["logins"]},
    {"module": "Event.routes", "prefix": "/fastapi/events", "tags": ["Events"]},
    {"module": "OpeningCash.routes", "prefix": "/fastapi/openingcashes", "tags": ["OpeningCash"]}, 
    {"module": "Payment.routes", "prefix": "/fastapi/payments", "tags": ["payments"]},
    {"module": "PettyCash.routes", "prefix": "/fastapi/pettycashes", "tags": ["PettyCash"]},
    {"module": "WhatsApp.routes", "prefix": "/fastapi/whatsappadmin", "tags": ["whatsappadmin"]},
    {"module": "WhatsappConfig.routes", "prefix": "/fastapi/whatsappconfig", "tags": ["WhatsappConfig"]},
    {"module": "WhatsappMessage.routes", "prefix": "/fastapi/whatsappmessage", "tags": ["WhatsappMessage"]},
    {"module": "dateTime.routes", "prefix": "/fastapi/datetime", "tags": ["datetime"]},
    {"module": "deliveryOrder.routes", "prefix": "/fastapi/deliveryorders", "tags": ["deliveryOrder"]},
    {"module": "deliveryType.routes", "prefix": "/fastapi/deliverytypes", "tags": ["deliverytypes"]},
    {"module": "AdvanceAmount.routes", "prefix": "/fastapi/advanceamounts", "tags": ["advanceamounts"]},
    {"module": "measurementType.routes", "prefix": "/fastapi/measurementtypes", "tags": ["measurementtypes"]},
    {"module": "assetManagement.routes", "prefix": "/fastapi/assetmanagements", "tags": ["assetmanagements"]},
    {"module": "posDevice.routes", "prefix": "/fastapi/posdevices", "tags": ["posdevices"]},
    {"module": "currency.routes", "prefix": "/fastapi/currencies", "tags": ["currencies"]},
    {"module": "Location.routes", "prefix": "/fastapi/Locations", "tags": ["Locations"]},
    {"module": "country.routes", "prefix": "/fastapi/countries", "tags": ["countries"]},
    {"module": "InventoryType.routes", "prefix": "/fastapi/inventorytypes", "tags": ["inventorytypes"]},
    {"module": "storeDispatch.routes", "prefix": "/fastapi/storedispatches", "tags": ["Storedispatches"]},
    {"module": "designation.routes", "prefix": "/fastapi/designations", "tags": ["designations"]},
    {"module": "rmRequest.routes", "prefix": "/fastapi/rmrequests", "tags": ["rmrequests"]},
    {"module": "customer.routes", "prefix": "/fastapi/customers", "tags": ["customer"]},
    {"module": "production_summary.routes", "prefix": "/fastapi/productionsummarys", "tags": ["productionsummarys"]},
    {"module": "dayEnd_Validations.routes", "prefix": "/fastapi/dayendvalidations", "tags": ["DayEndValidations"]},
	{"module": "HeldOrders.routes", "prefix": "/fastapi/heldorders", "tags": ["HeldOrder"]},

    # Daily activities API 
    {"module": "meterdetailsapi.routes", "prefix": "/fastapi/meterdetails", "tags": ["Meter Details"]},
    {"module": "eppricedetails.routes", "prefix": "/fastapi/eppricedetails", "tags": ["EP Price Details"]},
    {"module": "Ebreading.routes", "prefix": "/fastapi/ebreading", "tags": ["EB Reading"]},
    {"module": "LunchCount.routes", "prefix": "/fastapi/lunchcounts", "tags": ["Lunch Count"]},
    {"module": "MilkReceivings.routes", "prefix": "/fastapi/milkreceivings", "tags": ["Milk Receivings"]},
    {"module": "PhotoApi.routes", "prefix": "/fastapi/photoapis", "tags": ["Photo API"]},
    {"module": "empphoto.routes", "prefix": "/fastapi/empphotos", "tags": ["Employee Photo"]},
    {"module": "mobilesubmission.routes", "prefix": "/fastapi/mobilesubmissions", "tags": ["Mobile Submission"]},
    {"module": "kraSheet.routes", "prefix": "/fastapi/krasheets", "tags": ["KRA Sheet"]},
    {"module": "prayervideo.routes", "prefix": "/fastapi/prayervideos", "tags": ["Prayer Video"]},
    {"module": "BranchDisplay.routes", "prefix": "/fastapi/branchdisplays", "tags": ["Branch Display"]},
    {"module": "CleaningReport.routes", "prefix": "/fastapi/cleaningreports", "tags": ["Cleaning Report"]},
    {"module": "VideosApi.routes", "prefix": "/fastapi/davideos", "tags": ["davideos"]},
    {"module": "WarehouseReturn.routes", "prefix": "/fastapi/warehousereturns", "tags": ["warehouse returns"]},
    # Audio
    {"module": "audio.routes", "prefix": "/fastapi/audios", "tags": ["audios"]},
    # BillDesk
    {"module": "billDesk.routes", "prefix": "/fastapi/billdesks", "tags": ["billdesk"]},
    #ngxcorp
    {"module": "ngxwebiste_photos.routes", "prefix": "/fastapi/ngxphotos", "tags": ["ngxphotos"]},
    {"module": "customerDevice.routes", "prefix": "/fastapi/customerdevices", "tags": ["customerdevices"]},

]

def safe_include_router(route_info: dict):
    """
    Attempt to import the module and include its `router`.
    If any error occurs, log the error and continue.
    """
    module_name = route_info["module"]
    prefix = route_info["prefix"]
    tags = route_info["tags"]
    try:
        module = importlib.import_module(module_name)
        router = getattr(module, "router")
        app.include_router(router, prefix=prefix, tags=tags)
        logger.info(f"Included router from {module_name} with prefix {prefix}")
    except Exception as e:
        logger.error(f"Failed to include router from {module_name}: {e}")

# Loop over every route configuration and include it safely.
for route in routes_info:
    safe_include_router(route)

# Create database indexes on startup
@app.on_event("startup")
async def create_indexes():
    try:
        mongo_client = AsyncIOMotorClient(
            "mongodb://admin:YenE580nOOUE6cDhQERP@194.233.78.90:27017/admin?appName=mongosh+2.1.1&authSource=admin&authMechanism=SCRAM-SHA-256&replicaSet=yenerp-cluster"
        )
        db = mongo_client["reactfluttertest"]
        await db["branchwiseitem"].create_index([("branch.branchName", 1)])
        await db["branchwiseitem"].create_index([("varianceName", 1)])
        await db["branchwiseitem"].create_index([("branchId", 1)])
        await db["variances"].create_index([("varianceName", 1)])
        logger.info("Indexes created successfully.")
    except Exception as e:
        logger.error(f"Failed to create indexes: {e}")

# A simple root endpoint
@app.get("/")
def read_root():
    return {"message": "YEN ERP"}
