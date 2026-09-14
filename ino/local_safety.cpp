#include "local_safety.h"

#include "device_storage.h"
#include "hardware_bridge.h"

bool evaluateLocalCriticalCutoff(float currentA)
{
    float maxCurrentA = getLocalMaxCurrentA();

    if (currentA <= maxCurrentA)
    {
        return false;
    }

    if (relayState)
    {
        setRelay(false);
    }
    return true;
}
