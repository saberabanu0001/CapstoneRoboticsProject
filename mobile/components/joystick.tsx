import React, { useCallback } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { useRobot } from '@/context/robot-provider';
import {
  cmdJsonCmd,
  cmd_movition_ctrl,
  max_speed,
  slow_speed,
  MovementCommand,
} from '@/services/json-socket';

interface JoystickProps {
  onChange?: (value: { l: number; r: number }) => void;
}

interface Direction {
  key: string;
  label: string;
  rotation?: string;
  vector: { l: number; r: number };
  command?: MovementCommand;
}

const stopCommand: MovementCommand = { T: cmd_movition_ctrl, L: 0, R: 0 };

const directions: Direction[] = [
  {
    key: 'up-left',
    label: '∙',
    vector: { l: -1, r: 1 },
    command: { T: cmd_movition_ctrl, L: -slow_speed, R: -max_speed },
  },
  {
    key: 'up',
    label: '^',
    vector: { l: 1, r: 1 },
    command: { T: cmd_movition_ctrl, L: -max_speed, R: -max_speed },
  },
  {
    key: 'up-right',
    label: '∙',
    vector: { l: 1, r: 1 },
    command: { T: cmd_movition_ctrl, L: -max_speed, R: -slow_speed },
  },
  {
    key: 'left',
    label: '^',
    rotation: '-90deg',
    vector: { l: 1, r: 0 },
    command: { T: cmd_movition_ctrl, L: max_speed, R: -max_speed },
  },
  {
    key: 'center',
    label: '',
    vector: { l: 0, r: 0 },
    command: stopCommand,
  },
  {
    key: 'right',
    label: '^',
    rotation: '90deg',
    vector: { l: 0, r: 1 },
    command: { T: cmd_movition_ctrl, L: -max_speed, R: max_speed },
  },
  {
    key: 'down-left',
    label: '∙',
    vector: { l: 1, r: -1 },
    command: { T: cmd_movition_ctrl, L: slow_speed, R: max_speed },
  },
  {
    key: 'down',
    label: '^',
    rotation: '180deg',
    vector: { l: -1, r: -1 },
    command: { T: cmd_movition_ctrl, L: max_speed, R: max_speed },
  },
  {
    key: 'down-right',
    label: '∙',
    vector: { l: -1, r: 1 },
    command: { T: cmd_movition_ctrl, L: max_speed, R: slow_speed },
  },
];


export const Joystick: React.FC<JoystickProps> = ({ onChange }) => {
  const { baseUrl } = useRobot();

  const handlePressIn = useCallback(
    (direction: Direction) => {
      onChange?.(direction.vector);

      if (direction.command) {
        cmdJsonCmd({ ...direction.command }, baseUrl);
      }
    },
    [baseUrl, onChange],
  );

  const handlePressOut = useCallback(() => {
    onChange?.({ l: 0, r: 0 });
    cmdJsonCmd({ ...stopCommand }, baseUrl);
  }, [baseUrl, onChange]);

  return (
    <View style={styles.controller}>
      <View style={styles.grid}>
        <View style={styles.middleOverlay} pointerEvents="box-none">
          <Pressable
            onPressIn={() =>
              handlePressIn({
                key: 'center',
                label: '',
                vector: { l: 0, r: 0 },
                command: stopCommand,
              })
            }
            onPressOut={handlePressOut}
            style={styles.funcOuter}
          >
            {({ pressed }) => (
              <View style={styles.funcInnerShadow}>
                <View style={[styles.funcInner, pressed && styles.funcOuterActive]}>
                  <Text style={styles.funcText}>STOP</Text>
                </View>
              </View>)}
          </Pressable>
        </View>

        {directions.map((direction) => (
          <Pressable
            key={direction.key}
            onPressIn={() => handlePressIn(direction)}
            onPressOut={handlePressOut}
            style={styles.button}
          >
            {({ pressed }) => (
              <View style={styles.buttonContent}>
                {direction.label ? <Text style={[styles.buttonLabel,
                direction.rotation ? { transform: [{ rotate: direction.rotation }] } : null, pressed && { color: "#1DD1A1" }]}>{direction.label}</Text> : null}
              </View>
            )}
          </Pressable>
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  controller: {
    width: 242,
    alignSelf: 'center',
    backgroundImage: 'linear-gradient(#1E1E20,#1C1C1C)',
    borderWidth: 1,
    position: "relative",
    borderColor: '#2A2B30',
  },
  grid: {
    width: 240,
    height: 240,
    flexDirection: 'row',
    flexWrap: 'wrap',
    position: 'relative',
    overflow: 'hidden',
    shadowColor: "#000",
    shadowRadius: 1,
    shadowOffset: { width: 0, height: 10 },
    backgroundImage: 'linear-gradient(#1E1E20,#1C1C1C)',
  },
  middleOverlay: {
    position: 'absolute',
    top: 55,
    left: 60,
    width: 120,
    height: 120,
    borderRadius: 9999,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#161616',
    zIndex: 2,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  funcOuter: {
    width: 120,
    height: 120,
    borderRadius: 9999,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1E1E20',
  },
  funcOuterActive: {
    borderColor: '#1DD1A1',
  },
  funcInnerShadow: {
    width: 115,
    height: 115,
    borderRadius: 9999,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#161616',
  },
  funcInner: {
    width: 90,
    height: 90,
    borderRadius: 50,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1E1E20',
    borderWidth: 1,
    borderColor: '#2A2B30',
  },
  funcText: {
    color: '#E5E7EB',
    fontWeight: '700',
  },
  button: {
    width: 80,
    height: 80,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#1E1E20',
    borderColor: "transparent",
  },
  buttonContent: {
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
    height: '100%',
  },
  arrow: {
    width: 240,
    height: 240,
  },
  buttonLabel: {
    color: '#161616',
    fontSize: 42,
    fontWeight: 600
  },
});
