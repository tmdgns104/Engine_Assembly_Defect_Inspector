
#######################################
# Add common includes                 #
#######################################
opener_common_includes()

#######################################
# Add platform-specific includes      #
#######################################
opener_platform_support("INCLUDES")

if (OPENER_IS_DLR_DEVICE)
  set( SAMPLE_APP_DLR_ONLY_SRC ethlinkcbs.c )
endif()

find_package(Threads REQUIRED)
add_library(SAMPLE_APP sampleapplication.c engine_commissioning.c engine_ipc.c engine_evidence.c ${SAMPLE_APP_DLR_ONLY_SRC})
target_link_libraries( SAMPLE_APP NVDATA Threads::Threads )
