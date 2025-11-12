import os
from pydo import Client

#don't push the token to the repo
client = Client(token=os.environ.get("TOKEN"))

req = {
  "type": "power_on"
}

resp = client.droplet_actions.post(droplet_id=3164494, body=req)