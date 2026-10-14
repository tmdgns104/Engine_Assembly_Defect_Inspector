/*******************************************************************************
 * Copyright (c) 2012, Rockwell Automation, Inc.
 * All rights reserved.
 *
 ******************************************************************************/

#include <string.h>
#include <stdlib.h>
#include <stdbool.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

#include "opener_api.h"
#include "appcontype.h"
#include "trace.h"
#include "cipidentity.h"
#include "ciptcpipinterface.h"
#include "cipqos.h"
#include "nvdata.h"
#if defined(OPENER_ETHLINK_CNTRS_ENABLE) && 0 != OPENER_ETHLINK_CNTRS_ENABLE
  #include "cipethernetlink.h"
  #include "ethlinkcbs.h"
#endif

#define DEMO_APP_INPUT_ASSEMBLY_NUM                100 //0x064
#define DEMO_APP_OUTPUT_ASSEMBLY_NUM               150 //0x096
#define DEMO_APP_CONFIG_ASSEMBLY_NUM               151 //0x097
#define DEMO_APP_HEARTBEAT_INPUT_ONLY_ASSEMBLY_NUM  152 //0x098
#define DEMO_APP_HEARTBEAT_LISTEN_ONLY_ASSEMBLY_NUM 153 //0x099
#define DEMO_APP_EXPLICT_ASSEMBLY_NUM              154 //0x09A

/* global variables for demo application (4 assembly data fields)  ************/

EipUint8 g_assembly_data064[4]; /* Input */
EipUint8 g_assembly_data096[8]; /* Output */
EipUint8 g_assembly_data097[10]; /* Config */
EipUint8 g_assembly_data09A[32]; /* Explicit */

/* local functions */
static void EngineInitialize(void);

/* global functions called by the stack */
EipStatus ApplicationInitialization(void) {
  EngineInitialize();
  /* create 3 assembly object instances*/
  /*INPUT*/
  CreateAssemblyObject( DEMO_APP_INPUT_ASSEMBLY_NUM, g_assembly_data064,
                        sizeof(g_assembly_data064) );

  /*OUTPUT*/
  CreateAssemblyObject( DEMO_APP_OUTPUT_ASSEMBLY_NUM, g_assembly_data096,
                        sizeof(g_assembly_data096) );

  /*CONFIG*/
  CreateAssemblyObject( DEMO_APP_CONFIG_ASSEMBLY_NUM, g_assembly_data097,
                        sizeof(g_assembly_data097) );

  /*Heart-beat output assembly for Input only connections */
  CreateAssemblyObject(DEMO_APP_HEARTBEAT_INPUT_ONLY_ASSEMBLY_NUM, NULL, 0);

  /*Heart-beat output assembly for Listen only connections */
  CreateAssemblyObject(DEMO_APP_HEARTBEAT_LISTEN_ONLY_ASSEMBLY_NUM, NULL, 0);

  /* assembly for explicit messaging */
  CreateAssemblyObject( DEMO_APP_EXPLICT_ASSEMBLY_NUM, g_assembly_data09A,
                        sizeof(g_assembly_data09A) );

  ConfigureExclusiveOwnerConnectionPoint(0, DEMO_APP_OUTPUT_ASSEMBLY_NUM,
                                         DEMO_APP_INPUT_ASSEMBLY_NUM,
                                         DEMO_APP_CONFIG_ASSEMBLY_NUM);
  ConfigureInputOnlyConnectionPoint(0,
                                    DEMO_APP_HEARTBEAT_INPUT_ONLY_ASSEMBLY_NUM,
                                    DEMO_APP_INPUT_ASSEMBLY_NUM,
                                    DEMO_APP_CONFIG_ASSEMBLY_NUM);
  ConfigureListenOnlyConnectionPoint(0,
                                     DEMO_APP_HEARTBEAT_LISTEN_ONLY_ASSEMBLY_NUM,
                                     DEMO_APP_INPUT_ASSEMBLY_NUM,
                                     DEMO_APP_CONFIG_ASSEMBLY_NUM);

  /* For NV data support connect callback functions for each object class with
   *  NV data.
   */
  InsertGetSetCallback(GetCipClass(kCipQoSClassCode), NvQosSetCallback,
                       kNvDataFunc);
  InsertGetSetCallback(GetCipClass(kCipTcpIpInterfaceClassCode),
                       NvTcpipSetCallback,
                       kNvDataFunc);

#if defined(OPENER_ETHLINK_CNTRS_ENABLE) && 0 != OPENER_ETHLINK_CNTRS_ENABLE
  /* For the Ethernet Interface & Media Counters connect a PreGetCallback and
   *  a PostGetCallback.
   * The PreGetCallback is used to fetch the counters from the hardware.
   * The PostGetCallback is utilized by the GetAndClear service to clear
   *  the hardware counters after the current data have been transmitted.
   */
  {
    CipClass *p_eth_link_class = GetCipClass(kCipEthernetLinkClassCode);
    InsertGetSetCallback(p_eth_link_class,
                         EthLnkPreGetCallback,
                         kPreGetFunc);
    InsertGetSetCallback(p_eth_link_class,
                         EthLnkPostGetCallback,
                         kPostGetFunc);
    /* Specify the attributes for which the callback should be executed. */
    for (int idx = 0; idx < OPENER_ETHLINK_INSTANCE_CNT; ++idx)
    {
      CipAttributeStruct *p_eth_link_attr;
      CipInstance *p_eth_link_inst =
        GetCipInstance(p_eth_link_class, idx + 1);
      OPENER_ASSERT(p_eth_link_inst);

      /* Interface counters attribute */
      p_eth_link_attr = GetCipAttribute(p_eth_link_inst, 4);
      p_eth_link_attr->attribute_flags |= (kPreGetFunc | kPostGetFunc);
      /* Media counters attribute */
      p_eth_link_attr = GetCipAttribute(p_eth_link_inst, 5);
      p_eth_link_attr->attribute_flags |= (kPreGetFunc | kPostGetFunc);
    }
  }
#endif

  return kEipStatusOk;
}

/* The 4/8-byte commissioning application. No AI bridge and no input echo. */
#include "engine_callbacks.c.inc"
EipStatus ResetDevice(void) {
  /* add reset code here*/
  CloseAllConnections();
  CipQosUpdateUsedSetQosValues();
  return kEipStatusOk;
}

EipStatus ResetDeviceToInitialConfiguration(void) {
  /*rest the parameters */
  g_tcpip.encapsulation_inactivity_timeout = 120;
  CipQosResetAttributesToDefaultValues();
  /*than perform device reset*/
  ResetDevice();
  return kEipStatusOk;
}

void *
CipCalloc(size_t number_of_elements,
          size_t size_of_element) {
  return calloc(number_of_elements, size_of_element);
}

void CipFree(void *data) {
  free(data);
}

