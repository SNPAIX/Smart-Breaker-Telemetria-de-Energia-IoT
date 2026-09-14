// Puente hacia lo ya validado en code.ino — declaraciones, no
// implementaciones nuevas. Los módulos de la etapa 12 llaman a setRelay()
// y leen relayState tal como ya existen; nunca reimplementan el control
// del relé.
#pragma once

#include <Arduino.h>

void setRelay(bool state);
extern bool relayState;
