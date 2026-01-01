import useHealthConnect from '@/hook/useHealthConnect';
import {
  FontAwesome5,
  Ionicons,
  MaterialCommunityIcons,
} from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import React from 'react';
import {
  ActivityIndicator,
  Modal,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
  Alert,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import UserEmail from './userEmail';

export default function Index() {
  const [email, setEmail] = React.useState<string | null>(null);
  const [loadingEmail, setLoadingEmail] = React.useState(true);
  const [isUploading, setIsUploading] = React.useState(false);

  const {
    // ✅ 화면 표시용 (최신 하루치)
    sleep,
    weight,
    height,
    distance,
    steps,
    stepsCadence,
    totalCaloriesBurned,
    calories,
    oxygenSaturation,
    heartRate,
    restingHeartRate,
    // ✅ 서버 전송용 (최근 7일치 배열)
    dailyDataArray,
    error,
    hasPermissions,
    success,
    dataTimestamp,
    onPress: triggerFetch,
    refetch,
    revokeAccess,
  } = useHealthConnect();

  const [isRefreshing, setIsRefreshing] = React.useState(false);
  const [showPermissionModal, setShowPermissionModal] = React.useState(false);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await refetch();
    setIsRefreshing(false);
  };

  const handleInitialSync = async () => {
    if (!hasPermissions) {
      setShowPermissionModal(true);
    }
    await triggerFetch();
  };

  // ✅ 서버로 날짜별 데이터 전송
  const handleUploadToServer = async () => {
    if (!email) {
      Alert.alert('오류', '이메일이 설정되지 않았습니다.');
      return;
    }

    if (!dailyDataArray || dailyDataArray.length === 0) {
      Alert.alert(
        '오류',
        '전송할 데이터가 없습니다. 먼저 "Refresh Data"를 눌러주세요.'
      );
      return;
    }

    setIsUploading(true);

    try {
      console.log(`📡 Uploading ${dailyDataArray.length} days of data...`);

      // ✅ 날짜별로 서버에 전송
      let successCount = 0;
      let failCount = 0;

      for (const dayData of dailyDataArray) {
        // ✅ ZIP 파일 형식과 동일하게 변환
        const raw_json = {
          sleep_min: dayData.sleep,
          sleep_hr: dayData.sleep / 60,
          weight: dayData.weight,
          height_m: dayData.height,
          bmi: dayData.weight / (dayData.height * dayData.height),
          distance_km: dayData.distance,
          steps: dayData.steps,
          steps_cadence: dayData.stepsCadence,
          active_calories: dayData.calories,
          total_calories: dayData.totalCaloriesBurned,
          heart_rate: dayData.heartRate,
          resting_heart_rate: dayData.restingHeartRate,
          oxygen_saturation: dayData.oxygenSaturation,
          // 나머지 필드는 0으로 (ZIP과 동일한 구조)
          body_fat: 0,
          lean_body: 0,
          exercise_min: 0,
          flights: 0,
          calories_intake: 0,
          hrv: 0,
          systolic: 0,
          diastolic: 0,
          glucose: 0,
          walking_heart_rate: 0,
        };

        const payload = {
          user_id: email,
          date: dayData.date, // ✅ YYYY-MM-DD 형식
          raw_json,
          difficulty: '중',
          duration: 30,
        };

        try {
          console.log(`📤 Uploading ${dayData.date}...`);

          const response = await fetch(
            `${process.env.EXPO_PUBLIC_API_URL}/api/auto/upload`,
            {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
            }
          );

          if (!response.ok) {
            throw new Error(`Server response not ok for ${dayData.date}`);
          }

          const result = await response.json();
          console.log(`✅ ${dayData.date} uploaded successfully`);
          successCount++;
        } catch (error) {
          console.error(`❌ Failed to upload ${dayData.date}:`, error);
          failCount++;
        }
      }

      setIsUploading(false);

      // ✅ 결과 알림
      if (successCount === dailyDataArray.length) {
        Alert.alert(
          '업로드 완료!',
          `${successCount}일치 데이터가 성공적으로 업로드되었습니다.`
        );
      } else if (successCount > 0) {
        Alert.alert('부분 성공', `${successCount}일 성공, ${failCount}일 실패`);
      } else {
        Alert.alert('업로드 실패', '모든 데이터 업로드에 실패했습니다.');
      }
    } catch (error) {
      console.error('Upload error:', error);
      setIsUploading(false);
      Alert.alert('업로드 실패', String(error));
    }
  };

  const sleepHours = (sleep / 60).toFixed(1);

  React.useEffect(() => {
    const loadEmail = async () => {
      const savedEmail = await AsyncStorage.getItem('user_email');
      setEmail(savedEmail);
      setLoadingEmail(false);
    };
    loadEmail();
  }, []);

  if (loadingEmail) {
    return <View />;
  }

  if (!email) {
    return (
      <UserEmail
        onComplete={() => {
          AsyncStorage.getItem('user_email').then((value) => setEmail(value));
        }}
      />
    );
  }

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      {/* Header */}
      <LinearGradient
        colors={['#667eea', '#764ba2']}
        style={styles.header}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
      >
        <View style={styles.headerContent}>
          <MaterialCommunityIcons name="heart-pulse" size={32} color="white" />
          <Text style={styles.headerTitle}>Health Connect</Text>
        </View>
        {dataTimestamp && (
          <Text style={styles.lastUpdated}>
            Last updated: {new Date(dataTimestamp).toLocaleString()}
          </Text>
        )}
        {/* ✅ 수집된 날짜 표시 */}
        {dailyDataArray && dailyDataArray.length > 0 && (
          <Text style={styles.dataInfo}>
            📊 {dailyDataArray.length}일치 데이터 수집됨 (최신:{' '}
            {dailyDataArray[0]?.date})
          </Text>
        )}
      </LinearGradient>
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Error Banner */}
        {error && (
          <View style={styles.errorBanner}>
            <Ionicons name="alert-circle" size={24} color="#ef4444" />
            <Text style={styles.errorText}>{error}</Text>
          </View>
        )}

        {/* No Permission State */}
        {!hasPermissions && !error && (
          <View style={styles.emptyState}>
            <View style={styles.emptyIconContainer}>
              <MaterialCommunityIcons
                name="shield-lock-outline"
                size={80}
                color="#9ca3af"
              />
            </View>
            <Text style={styles.emptyTitle}>Permission Required</Text>
            <Text style={styles.emptyDescription}>
              Grant access to Health Connect to view your health data
            </Text>
            <Pressable style={styles.primaryButton} onPress={handleInitialSync}>
              <MaterialCommunityIcons
                name="shield-check"
                size={20}
                color="white"
              />
              <Text style={styles.primaryButtonText}>Grant Access</Text>
            </Pressable>
          </View>
        )}

        {/* No Data State */}
        {hasPermissions &&
          success &&
          sleep === 0 &&
          weight === 0 &&
          height === 0 &&
          distance === 0 &&
          steps === 0 &&
          stepsCadence === 0 &&
          totalCaloriesBurned === 0 &&
          calories === 0 &&
          oxygenSaturation === 0 &&
          heartRate === 0 &&
          restingHeartRate === 0 && (
            <View style={styles.emptyState}>
              <View style={styles.emptyIconContainer}>
                <MaterialCommunityIcons
                  name="database-off-outline"
                  size={80}
                  color="#9ca3af"
                />
              </View>
              <Text style={styles.emptyTitle}>No Data Available</Text>
              <Text style={styles.emptyDescription}>
                No health data found for today. Make sure your fitness tracker
                is syncing data.
              </Text>
            </View>
          )}

        {/* Data Cards - 최신 하루치만 표시 */}
        {hasPermissions &&
          (sleep > 0 ||
            weight > 0 ||
            height > 0 ||
            distance > 0 ||
            steps > 0 ||
            stepsCadence > 0 ||
            totalCaloriesBurned > 0 ||
            calories > 0 ||
            oxygenSaturation > 0 ||
            heartRate > 0 ||
            restingHeartRate > 0) && (
            <View style={styles.cardsContainer}>
              {/* 1. Sleep Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#8b5cf6', '#7c3aed']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <Ionicons name="moon" size={28} color="white" />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Sleep</Text>
                    <Text style={styles.cardValue}>{sleepHours}</Text>
                    <Text style={styles.cardUnit}>hours</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 2. Weight Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#10b981', '#059669']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <MaterialCommunityIcons
                      name="scale-balance"
                      size={28}
                      color="white"
                    />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Weight</Text>
                    <Text style={styles.cardValue}>
                      {weight ? weight.toFixed(1) : '--'}
                    </Text>
                    <Text style={styles.cardUnit}>kg</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 3 Height Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#34d399', '#10b981']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <FontAwesome5
                      name="ruler-vertical"
                      size={28}
                      color="white"
                    />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Height</Text>
                    <Text style={styles.cardValue}>
                      {height ? (height * 100).toFixed(0) : '--'}
                    </Text>
                    <Text style={styles.cardUnit}>cm</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 4. Distance Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#3b82f6', '#2563eb']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <MaterialCommunityIcons
                      name="map-marker-distance"
                      size={28}
                      color="white"
                    />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Distance</Text>
                    <Text style={styles.cardValue}>
                      {distance ? distance.toFixed(2) : '--'}
                    </Text>
                    <Text style={styles.cardUnit}>km</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 5. Steps Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#3b82f6', '#2563eb']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <FontAwesome5 name="walking" size={28} color="white" />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Steps</Text>
                    <Text style={styles.cardValue}>
                      {steps ? steps.toLocaleString() : '--'}
                    </Text>
                    <Text style={styles.cardUnit}>steps</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 6. Steps Cadence Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#06b6d4', '#0891b2']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <MaterialCommunityIcons
                      name="run-fast"
                      size={28}
                      color="white"
                    />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Cadence</Text>
                    <Text style={styles.cardValue}>{stepsCadence || '--'}</Text>
                    <Text style={styles.cardUnit}>steps/min</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 7. Total Calories Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#f59e0b', '#d97706']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <Ionicons name="flame" size={28} color="white" />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Total Calories</Text>
                    <Text style={styles.cardValue}>
                      {totalCaloriesBurned || '--'}
                    </Text>
                    <Text style={styles.cardUnit}>kcal</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 8. Active Calories Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#ef4444', '#dc2626']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <MaterialCommunityIcons
                      name="fire"
                      size={28}
                      color="white"
                    />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Active Calories</Text>
                    <Text style={styles.cardValue}>{calories || '--'}</Text>
                    <Text style={styles.cardUnit}>kcal</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 9. Oxygen Saturation Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#06b6d4', '#0284c7']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <MaterialCommunityIcons
                      name="water-percent"
                      size={28}
                      color="white"
                    />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Oxygen</Text>
                    <Text style={styles.cardValue}>
                      {oxygenSaturation ? oxygenSaturation.toFixed(1) : '--'}
                    </Text>
                    <Text style={styles.cardUnit}>%</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 10. Heart Rate Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#ec4899', '#db2777']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <FontAwesome5 name="heartbeat" size={28} color="white" />
                  </View>
                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Heart Rate</Text>
                    <Text style={styles.cardValue}>{heartRate || '--'}</Text>
                    <Text style={styles.cardUnit}>bpm</Text>
                  </View>
                </LinearGradient>
              </View>
              {/* 11. Resting Heart Rate Card */}
              <View style={styles.card}>
                <LinearGradient
                  colors={['#9d174d', '#f43f5e']}
                  style={styles.cardGradient}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 1 }}
                >
                  <View style={styles.cardIconContainer}>
                    <MaterialCommunityIcons
                      name="heart-cog-outline"
                      size={32}
                      color="white"
                    />
                  </View>

                  <View style={styles.cardContent}>
                    <Text style={styles.cardLabel}>Resting Heart Rate</Text>
                    <Text style={styles.cardValue}>
                      {restingHeartRate || '--'}
                    </Text>
                    <Text style={styles.cardUnit}>bpm</Text>
                  </View>
                </LinearGradient>
              </View>
            </View>
          )}
      </ScrollView>
      {/* Bottom Actions */}
      {hasPermissions && (
        <View style={styles.bottomActions}>
          {/* --- ① Refresh Button --- */}
          <Pressable
            style={styles.bottomButton}
            onPress={handleRefresh}
            disabled={isRefreshing}
          >
            <Text style={styles.refreshButtonText}>
              {isRefreshing ? 'Refreshing...' : 'Refresh\nData'}
            </Text>
          </Pressable>

          {/* --- ② Upload to Server Button --- */}
          <Pressable
            style={[styles.bottomButton, isUploading && styles.buttonDisabled]}
            onPress={handleUploadToServer}
            disabled={isUploading}
          >
            {isUploading ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={styles.bottomButtonText}>Upload to Server</Text>
            )}
          </Pressable>

          {/* --- ③ Revoke Access Button --- */}
          <Pressable style={styles.bottomButton} onPress={revokeAccess}>
            <Text style={styles.bottomButtonText}>Revoke Access</Text>
          </Pressable>

          {/* --- ④ Change Email Button --- */}
          <Pressable
            style={styles.bottomButton}
            onPress={async () => {
              await AsyncStorage.removeItem('user_email');
              setEmail(null);
            }}
          >
            <Text style={styles.bottomButtonText}>Change Email</Text>
          </Pressable>
        </View>
      )}

      {/* Permission Modal */}
      <Modal
        visible={showPermissionModal && !hasPermissions}
        transparent
        animationType="fade"
        onRequestClose={() => setShowPermissionModal(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalIconContainer}>
              <MaterialCommunityIcons
                name="shield-check"
                size={64}
                color="#667eea"
              />
            </View>
            <Text style={styles.modalTitle}>Health Connect Access</Text>
            <Text style={styles.modalDescription}>
              This app needs permission to read your health data from Health
              Connect including:
            </Text>

            <View style={styles.permissionList}>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Sleep Sessions</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Weight</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Height</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Distance</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Steps</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Steps Cadence</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Calories</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Oxygen Saturation</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Heart Rate</Text>
              </View>
              <View style={styles.permissionItem}>
                <MaterialCommunityIcons
                  name="check-circle"
                  size={20}
                  color="#10b981"
                />
                <Text style={styles.permissionText}>Resting Heart Rate</Text>
              </View>
            </View>
            <Pressable
              style={styles.modalButton}
              onPress={() => {
                setShowPermissionModal(false);
                triggerFetch();
              }}
            >
              <Text style={styles.modalButtonText}>Continue</Text>
            </Pressable>
            <Pressable
              style={styles.modalCancelButton}
              onPress={() => setShowPermissionModal(false)}
            >
              <Text style={styles.modalCancelButtonText}>Cancel</Text>
            </Pressable>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8fafc',
  },
  header: {
    paddingTop: 60,
    paddingBottom: 24,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 30,
    borderBottomRightRadius: 30,
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: 'white',
  },
  lastUpdated: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 8,
  },
  dataInfo: {
    fontSize: 12,
    color: 'rgba(255, 255, 255, 0.9)',
    marginTop: 4,
    fontWeight: '500',
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 100,
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fef2f2',
    padding: 16,
    borderRadius: 12,
    gap: 12,
    marginBottom: 20,
    borderLeftWidth: 4,
    borderLeftColor: '#ef4444',
  },
  errorText: {
    flex: 1,
    color: '#991b1b',
    fontSize: 14,
    fontWeight: '500',
  },
  emptyState: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 60,
    paddingHorizontal: 20,
  },
  emptyIconContainer: {
    marginBottom: 24,
  },
  emptyTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 12,
    textAlign: 'center',
  },
  emptyDescription: {
    fontSize: 16,
    color: '#6b7280',
    textAlign: 'center',
    lineHeight: 24,
    marginBottom: 32,
  },
  primaryButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#667eea',
    paddingVertical: 16,
    paddingHorizontal: 32,
    borderRadius: 12,
    gap: 8,
    elevation: 4,
    shadowColor: '#667eea',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  primaryButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  cardsContainer: {
    gap: 16,
  },
  card: {
    borderRadius: 16,
    overflow: 'hidden',
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 8,
  },
  cardGradient: {
    padding: 20,
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: 100,
  },
  cardIconContainer: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 16,
  },
  cardContent: {
    flex: 1,
  },
  cardLabel: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.9)',
    fontWeight: '500',
    marginBottom: 4,
  },
  cardValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: 'white',
  },
  cardUnit: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: 2,
  },
  bottomActions: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'white',
    padding: 20,
    paddingBottom: 30,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    flexDirection: 'row',
    gap: 3,
    elevation: 8,
    shadowColor: '#022264ff',
    shadowOffset: { width: 0, height: -4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
  },
  bottomButton: {
    flex: 1,
    backgroundColor: '#022264ff',
    paddingVertical: 16,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  bottomButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  refreshButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
    flexWrap: 'wrap',
    lineHeight: 18,
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  modalContent: {
    backgroundColor: 'white',
    borderRadius: 24,
    padding: 32,
    width: '100%',
    maxWidth: 400,
    alignItems: 'center',
  },
  modalIconContainer: {
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#1f2937',
    marginBottom: 12,
    textAlign: 'center',
  },
  modalDescription: {
    fontSize: 15,
    color: '#6b7280',
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
  },
  permissionList: {
    alignSelf: 'stretch',
    backgroundColor: '#f9fafb',
    padding: 16,
    borderRadius: 12,
    gap: 12,
    marginBottom: 24,
  },
  permissionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  permissionText: {
    fontSize: 15,
    color: '#374151',
    fontWeight: '500',
  },
  modalButton: {
    backgroundColor: '#667eea',
    paddingVertical: 16,
    paddingHorizontal: 48,
    borderRadius: 12,
    width: '100%',
    alignItems: 'center',
    marginBottom: 12,
  },
  modalButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  modalCancelButton: {
    paddingVertical: 12,
  },
  modalCancelButtonText: {
    color: '#6b7280',
    fontSize: 15,
    fontWeight: '500',
  },
});
