#!/bin/bash
DISPLAY_PATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

phoebus -resource "file:$DISPLAY_PATH/stream_overview.bob?P=VALVE-DEMO-01&app=display_runtime"