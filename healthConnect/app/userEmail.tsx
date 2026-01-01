import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  Pressable,
  StyleSheet,
  Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function UserEmail({ onComplete }: { onComplete: () => void }) {
  const [email, setEmail] = useState('');

  const handleSave = async () => {
    if (!email.includes('@')) {
      Alert.alert('이메일 형식이 올바르지 않습니다.');
      return;
    }

    await AsyncStorage.setItem('user_email', email);
    Alert.alert('이메일 저장 완료!', email);

    onComplete(); // 메인 화면으로 이동
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>이메일을 입력하세요</Text>

      <TextInput
        placeholder="example@email.com"
        placeholderTextColor="#999"
        style={styles.input}
        value={email}
        autoCapitalize="none"
        keyboardType="email-address"
        onChangeText={setEmail}
      />

      <Pressable style={styles.button} onPress={handleSave}>
        <Text style={styles.buttonText}>확인</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0A0A23',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  title: {
    color: 'white',
    fontSize: 22,
    marginBottom: 24,
  },
  input: {
    width: '100%',
    backgroundColor: 'white',
    padding: 14,
    borderRadius: 12,
    marginBottom: 20,
    fontSize: 16,
  },
  button: {
    backgroundColor: '#1E3A8A',
    paddingVertical: 15,
    paddingHorizontal: 40,
    borderRadius: 12,
  },
  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: '600',
  },
});
