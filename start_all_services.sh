#!/bin/bash

# 启动所有标注服务
conda activate tool
# echo "🚀 Starting annotation service on port 7800..."
# python src/main_multi.py --task annotation &

echo "🚀 Starting whole_annotation service on port 7801..."
python src/main_multi.py --task whole_annotation --dev &

echo "🚀 Starting part_annotation service on port 7802..."
python src/main_multi.py --task part_annotation --dev &

echo -e "\n✅ All services are starting in the background."
echo "You can access them at:"
# echo "  - Object Annotation: http://localhost:7800"
echo "  - Whole Annotation:  http://localhost:7801"
echo "  - Part Annotation:   http://localhost:7802"
echo -e "\nTo stop all services, you can close this terminal or use the command: killall python"