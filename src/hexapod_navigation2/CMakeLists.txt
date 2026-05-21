cmake_minimum_required(VERSION 3.8)
project(hexapod_navigation2)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)

add_executable(hexapod_navigation2_node src/hexapod_navigation2_node.cpp)
ament_target_dependencies(hexapod_navigation2_node rclcpp)

install(TARGETS
  hexapod_navigation2_node
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch config
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

install(DIRECTORY launch maps config
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
