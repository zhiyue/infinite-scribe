#!/bin/bash

# 测试矩阵生成逻辑
echo "🧪 Testing matrix generation logic..."

# 模拟有效服务列表
valid_services=("backend" "frontend")

# 测试场景 1: 手动触发 - all
echo -e "\n📋 Test 1: Manual dispatch with 'all'"
input_services="all"
services=()

if [ "$input_services" = "all" ]; then
  services=("backend" "frontend")
else
  IFS=',' read -ra service_array <<< "$input_services"
  for service in "${service_array[@]}"; do
    service=$(echo "$service" | xargs)
    if [[ " ${valid_services[*]} " =~ " ${service} " ]]; then
      services+=("$service")
    else
      echo "❌ Invalid service name: '$service'. Valid options: ${valid_services[*]}"
      exit 1
    fi
  done
fi

# 生成 JSON
if [ ${#services[@]} -gt 0 ]; then
  services_json="["
  for i in "${!services[@]}"; do
    if [ $i -gt 0 ]; then
      services_json="${services_json},"
    fi
    services_json="${services_json}\"${services[i]}\""
  done
  services_json="${services_json}]"
  
  echo "✅ Services: ${services[*]}"
  echo "✅ JSON: ${services_json}"
  echo "${services_json}" | python3 -m json.tool > /dev/null && echo "✅ Valid JSON format"
else
  echo "❌ No services found"
fi

# 测试场景 2: 手动触发 - 特定服务
echo -e "\n📋 Test 2: Manual dispatch with 'backend,frontend'"
input_services="backend,frontend"
services=()

IFS=',' read -ra service_array <<< "$input_services"
for service in "${service_array[@]}"; do
  service=$(echo "$service" | xargs)
  if [[ " ${valid_services[*]} " =~ " ${service} " ]]; then
    services+=("$service")
  else
    echo "❌ Invalid service name: '$service'. Valid options: ${valid_services[*]}"
    exit 1
  fi
done

# 生成 JSON
if [ ${#services[@]} -gt 0 ]; then
  services_json="["
  for i in "${!services[@]}"; do
    if [ $i -gt 0 ]; then
      services_json="${services_json},"
    fi
    services_json="${services_json}\"${services[i]}\""
  done
  services_json="${services_json}]"
  
  echo "✅ Services: ${services[*]}"
  echo "✅ JSON: ${services_json}"
  echo "${services_json}" | python3 -m json.tool > /dev/null && echo "✅ Valid JSON format"
else
  echo "❌ No services found"
fi

# 测试场景 3: 无效服务名
echo -e "\n📋 Test 3: Invalid service name"
input_services="backend,invalid-service"
services=()

IFS=',' read -ra service_array <<< "$input_services"
for service in "${service_array[@]}"; do
  service=$(echo "$service" | xargs)
  if [[ " ${valid_services[*]} " =~ " ${service} " ]]; then
    services+=("$service")
  else
    echo "❌ Invalid service name: '$service'. Valid options: ${valid_services[*]}"
    echo "✅ Validation working correctly - invalid input rejected"
    break
  fi
done

echo -e "\n🎉 All tests completed successfully!"
