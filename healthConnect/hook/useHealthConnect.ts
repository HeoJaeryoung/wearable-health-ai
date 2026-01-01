import { useCallback, useEffect, useState } from 'react';
import { Platform, Alert } from 'react-native';
import {
  initialize,
  requestPermission,
  readRecords,
  getGrantedPermissions,
  openHealthConnectSettings,
} from 'react-native-health-connect';
import type {
  Permission,
  WriteExerciseRoutePermission,
  BackgroundAccessPermission,
  ReadHealthDataHistoryPermission,
} from 'react-native-health-connect/lib/typescript/types';
import { TimeRangeFilter } from 'react-native-health-connect/lib/typescript/types/base.types';

const RECORD_TYPES = {
  SLEEP: 'SleepSession',
  WEIGHT: 'Weight',
  HEIGHT: 'Height',
  DISTANCE: 'Distance',
  STEPS: 'Steps',
  STEPS_CADENCE: 'StepsCadence',
  TOTAL_CALORIES: 'TotalCaloriesBurned',
  CALORIES: 'ActiveCaloriesBurned',
  OXYGEN_SATURATION: 'OxygenSaturation',
  HEART_RATE: 'HeartRate',
  RESTING_HEART_RATE: 'RestingHeartRate',
} as const;

const REQUIRED_PERMISSIONS: Permission[] = [
  { accessType: 'read', recordType: RECORD_TYPES.SLEEP },
  { accessType: 'read', recordType: RECORD_TYPES.WEIGHT },
  { accessType: 'read', recordType: RECORD_TYPES.HEIGHT },
  { accessType: 'read', recordType: RECORD_TYPES.DISTANCE },
  { accessType: 'read', recordType: RECORD_TYPES.STEPS },
  { accessType: 'read', recordType: RECORD_TYPES.STEPS_CADENCE },
  { accessType: 'read', recordType: RECORD_TYPES.TOTAL_CALORIES },
  { accessType: 'read', recordType: RECORD_TYPES.CALORIES },
  { accessType: 'read', recordType: RECORD_TYPES.OXYGEN_SATURATION },
  { accessType: 'read', recordType: RECORD_TYPES.HEART_RATE },
  { accessType: 'read', recordType: RECORD_TYPES.RESTING_HEART_RATE },
];

type AllHealthConnectPermission =
  | Permission
  | WriteExerciseRoutePermission
  | BackgroundAccessPermission
  | ReadHealthDataHistoryPermission;

// ✅ 날짜별 데이터 타입 정의
interface DailyHealthData {
  date: string; // YYYY-MM-DD 형식
  sleep: number;
  weight: number;
  height: number;
  distance: number;
  steps: number;
  stepsCadence: number;
  totalCaloriesBurned: number;
  calories: number;
  oxygenSaturation: number;
  heartRate: number;
  restingHeartRate: number;
}

const useHealthConnect = () => {
  // ✅ 최신 하루치 데이터 (화면 표시용)
  const [data, setData] = useState({
    sleep: 0,
    weight: 0,
    height: 0,
    distance: 0,
    steps: 0,
    stepsCadence: 0,
    totalCaloriesBurned: 0,
    calories: 0,
    oxygenSaturation: 0,
    heartRate: 0,
    restingHeartRate: 0,
  });

  // ✅ 최근 1일치 날짜별 데이터 (서버 전송용)
  const [dailyDataArray, setDailyDataArray] = useState<DailyHealthData[]>([]);

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [dataTimestamp, setDataTimestamp] = useState<string | null>(null);
  const [permissions, setPermissions] = useState<AllHealthConnectPermission[]>(
    []
  );
  const [isInitialized, setIsInitialized] = useState(false);

  const hasAllPermissions = useCallback(() => {
    return REQUIRED_PERMISSIONS.every((req) =>
      permissions.some(
        (p) =>
          p.recordType === req.recordType && p.accessType === req.accessType
      )
    );
  }, [permissions]);

  useEffect(() => {
    if (Platform.OS !== 'android') return;

    const init = async () => {
      try {
        const initialized = await initialize();
        if (!initialized) {
          setError('Failed to initialize Health Connect');
          return;
        }
        setIsInitialized(true);

        const granted = await getGrantedPermissions();
        setPermissions(granted);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Initialization failed');
      }
    };
    init();
  }, []);

  const requestPermissions = useCallback(async () => {
    if (!isInitialized) {
      setError('Health Connect not initialized');
      return { success: false, granted: [] };
    }
    try {
      const granted = await requestPermission(REQUIRED_PERMISSIONS);
      setPermissions(granted);

      const hasPerms = REQUIRED_PERMISSIONS.every((req) =>
        granted.some(
          (p) =>
            p.recordType === req.recordType && p.accessType === req.accessType
        )
      );

      setError(hasPerms ? null : 'Some permissions denied');
      return { success: hasPerms, granted };
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Permission request failed'
      );
      return { success: false, granted: [] };
    }
  }, [isInitialized]);

  // ✅ 하루치 데이터 가져오기 함수
  const fetchDayData = async (dateStr: string): Promise<DailyHealthData> => {
    // ✅ 로컬 시간 기준으로 날짜 범위 생성
    const [year, month, day] = dateStr.split('-').map(Number);

    // 로컬 시간 00:00:00
    const startDate = new Date(year, month - 1, day, 0, 0, 0, 0);

    // 로컬 시간 23:59:59
    const endDate = new Date(year, month - 1, day, 23, 59, 59, 999);

    const startTime = startDate.toISOString();
    const endTime = endDate.toISOString();

    console.log(`   📅 ${dateStr}: ${startTime} ~ ${endTime}`);

    const timeRangeFilter: TimeRangeFilter = {
      operator: 'between',
      startTime,
      endTime,
    };

    let totalSleep = 0;
    let latestWeight = 0;
    let latestHeight = 0;
    let totalDistanceMeters = 0;
    let totalSteps = 0;
    let latestCadence = 0;
    let totalCaloriesBurned = 0;
    let totalActiveCalories = 0;
    let latestOxygenSaturation = 0;
    let latestHeartRate = 0;
    let latestRestingHeartRate = 0;

    try {
      // 1. Sleep
      const sleepResult = await readRecords(RECORD_TYPES.SLEEP, {
        timeRangeFilter,
      });
      const sleepRecords = sleepResult.records || [];
      totalSleep = sleepRecords.reduce((sum, cur) => {
        if (cur.startTime && cur.endTime) {
          const start = new Date(cur.startTime).getTime();
          const end = new Date(cur.endTime).getTime();
          const minutes = (end - start) / (1000 * 60);
          return sum + minutes;
        }
        return sum;
      }, 0);

      // 2. Weight
      const weightResult = await readRecords(RECORD_TYPES.WEIGHT, {
        timeRangeFilter,
      });
      if (weightResult.records && weightResult.records.length > 0) {
        const latestRecord = weightResult.records[0];
        if (
          'weight' in latestRecord &&
          latestRecord.weight &&
          'inKilograms' in latestRecord.weight
        ) {
          latestWeight = (latestRecord.weight as { inKilograms: number })
            .inKilograms;
        }
      }

      // 3. Height
      const heightResult = await readRecords(RECORD_TYPES.HEIGHT, {
        timeRangeFilter,
      });
      if (heightResult.records && heightResult.records.length > 0) {
        const latestRecord = heightResult.records[0];
        if (
          'height' in latestRecord &&
          latestRecord.height &&
          'inMeters' in latestRecord.height
        ) {
          latestHeight = (latestRecord.height as { inMeters: number }).inMeters;
        }
      }

      // 4. Distance
      const distanceResult = await readRecords(RECORD_TYPES.DISTANCE, {
        timeRangeFilter,
      });
      const distanceRecords = distanceResult.records || [];
      totalDistanceMeters = distanceRecords.reduce(
        (sum, cur) =>
          sum + ((cur.distance as { inMeters: number })?.inMeters || 0),
        0
      );

      // 5. Steps
      const stepsResult = await readRecords(RECORD_TYPES.STEPS, {
        timeRangeFilter,
      });
      const stepsRecords = stepsResult.records || [];
      totalSteps = stepsRecords.reduce((sum, cur) => sum + (cur.count || 0), 0);

      // 6. Steps Cadence
      const cadenceResult = await readRecords(RECORD_TYPES.STEPS_CADENCE, {
        timeRangeFilter,
      });
      const cadenceRecords = cadenceResult.records || [];
      if (cadenceRecords.length > 0) {
        const allSamples: any[] = [];
        cadenceRecords.forEach((record) => {
          if ('samples' in record && Array.isArray(record.samples)) {
            allSamples.push(...record.samples);
          }
        });
        if (allSamples.length > 0) {
          const latest = allSamples.reduce((prev, curr) =>
            new Date(curr.time) > new Date(prev.time) ? curr : prev
          );
          latestCadence = latest.rate || 0;
        }
      }

      // 7. Total Calories
      const totalCaloriesResult = await readRecords(
        RECORD_TYPES.TOTAL_CALORIES,
        { timeRangeFilter }
      );
      const totalCaloriesRecords = totalCaloriesResult.records || [];
      totalCaloriesBurned = totalCaloriesRecords.reduce(
        (sum, cur) => sum + (cur.energy?.inKilocalories || 0),
        0
      );

      // 8. Active Calories
      const caloriesResult = await readRecords(RECORD_TYPES.CALORIES, {
        timeRangeFilter,
      });
      const caloriesRecords = caloriesResult.records || [];
      totalActiveCalories = caloriesRecords.reduce(
        (sum, cur) => sum + (cur.energy?.inKilocalories || 0),
        0
      );

      // 9. Heart Rate
      const hrResult = await readRecords(RECORD_TYPES.HEART_RATE, {
        timeRangeFilter,
      });
      const hrRecords = hrResult.records || [];
      let latestSampleTime = 0;
      for (const record of hrRecords) {
        if ('samples' in record && Array.isArray(record.samples)) {
          for (const sample of record.samples) {
            if ('beatsPerMinute' in sample) {
              const sampleTime = new Date(sample.time).getTime();
              if (sampleTime > latestSampleTime) {
                latestSampleTime = sampleTime;
                latestHeartRate = sample.beatsPerMinute || 0;
              }
            }
          }
        }
      }

      // 10. Oxygen Saturation
      const osResult = await readRecords(RECORD_TYPES.OXYGEN_SATURATION, {
        timeRangeFilter,
      });
      const osRecords = osResult.records || [];
      for (const record of osRecords) {
        if ('samples' in record && Array.isArray(record.samples)) {
          for (const sample of record.samples) {
            if (
              'percentage' in sample &&
              sample.percentage &&
              'inPercent' in sample.percentage
            ) {
              const sampleTime = new Date(sample.time).getTime();
              if (sampleTime > latestSampleTime) {
                latestSampleTime = sampleTime;
                latestOxygenSaturation = (
                  sample.percentage as { inPercent: number }
                ).inPercent;
              }
            }
          }
        }
      }

      // 11. Resting Heart Rate
      const rhrResult = await readRecords(RECORD_TYPES.RESTING_HEART_RATE, {
        timeRangeFilter,
      });
      if (rhrResult.records && rhrResult.records.length > 0) {
        const latestRecord = rhrResult.records[0];
        if (latestRecord !== null && typeof latestRecord === 'object') {
          if (
            'average' in latestRecord &&
            latestRecord.average !== null &&
            typeof latestRecord.average === 'object'
          ) {
            const averageObj = latestRecord.average;
            if ('beatsPerMinute' in averageObj) {
              latestRestingHeartRate = (
                averageObj as { beatsPerMinute: number }
              ).beatsPerMinute;
            }
          }
        }
      }
    } catch (err) {
      console.error(`❌ Error fetching data for ${dateStr}:`, err);
    }

    const totalDistanceKm = totalDistanceMeters / 1000;

    return {
      date: dateStr,
      sleep: Math.round(totalSleep),
      weight: Math.round(latestWeight * 10) / 10,
      height: Math.round(latestHeight * 100) / 100,
      distance: Math.round(totalDistanceKm * 100) / 100,
      steps: totalSteps,
      stepsCadence: Math.round(latestCadence),
      totalCaloriesBurned: Math.round(totalCaloriesBurned),
      calories: Math.round(totalActiveCalories),
      oxygenSaturation: Math.round(latestOxygenSaturation * 10) / 10,
      heartRate: latestHeartRate,
      restingHeartRate: Math.round(latestRestingHeartRate),
    };
  };

  // ✅ 최근 1일치 데이터 가져오기
  const fetchData = useCallback(
    async (numDays?: number) => {
      const hasPerms = REQUIRED_PERMISSIONS.every((req) =>
        permissions.some(
          (p) =>
            p.recordType === req.recordType && p.accessType === req.accessType
        )
      );

      if (!isInitialized || !hasPerms) {
        setError('Permissions or initialization missing');
        return;
      }

      try {
        setError(null);
        setSuccess(false);

        // ✅ 로컬 시간 그대로 사용 (기기가 한국이면 자동으로 한국 시간)
        const today = new Date();
        today.setHours(0, 0, 0, 0); // 시간 초기화

        // ✅ 디버깅 로그
        console.log('====================================');
        console.log('📅 날짜 계산 시작');
        console.log(`   현재 시각: ${new Date().toISOString()}`);
        console.log(
          `   오늘 날짜: ${today.getFullYear()}-${String(
            today.getMonth() + 1
          ).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
        );
        console.log('====================================');

        const dailyData: DailyHealthData[] = [];
        const days = numDays || 1;

        console.log(`📊 ${days}일치 데이터 수집 시작`);

        for (let i = 0; i < days; i++) {
          // ✅ 로컬 시간 기준으로 날짜 계산
          const targetDate = new Date(today);
          targetDate.setDate(targetDate.getDate() - i);

          // ✅ YYYY-MM-DD 형식으로 변환
          const year = targetDate.getFullYear();
          const month = String(targetDate.getMonth() + 1).padStart(2, '0');
          const day = String(targetDate.getDate()).padStart(2, '0');
          const dateStr = `${year}-${month}-${day}`;

          console.log(`   [${i}] 수집 날짜: ${dateStr}`);

          const dayData = await fetchDayData(dateStr);

          console.log(
            `   [${i}] 걸음: ${dayData.steps}, 수면: ${dayData.sleep}분`
          );

          dailyData.push(dayData);

          if ((i + 1) % 10 === 0 || i === days - 1) {
            console.log(`   진행: ${i + 1}/${days} 완료`);
          }
        }

        console.log(`✅ 데이터 수집 완료: ${dailyData.length}일`);
        console.log('📋 수집된 날짜 목록:');
        dailyData.forEach((data, idx) => {
          const hasData = data.steps > 0 || data.sleep > 0 || data.weight > 0;
          console.log(
            `   [${idx}] ${data.date} - ${
              hasData ? '✅ 데이터 있음' : '⚠️ 빈 데이터'
            }`
          );
        });

        const latestData = dailyData[0];
        setData({
          sleep: latestData.sleep,
          weight: latestData.weight,
          height: latestData.height,
          distance: latestData.distance,
          steps: latestData.steps,
          stepsCadence: latestData.stepsCadence,
          totalCaloriesBurned: latestData.totalCaloriesBurned,
          calories: latestData.calories,
          oxygenSaturation: latestData.oxygenSaturation,
          heartRate: latestData.heartRate,
          restingHeartRate: latestData.restingHeartRate,
        });

        setDailyDataArray(dailyData);
        setDataTimestamp(new Date().toISOString());
        setSuccess(true);
      } catch (err) {
        console.error('Fetch error:', err);
        setError(err instanceof Error ? err.message : 'Fetch failed');
        setSuccess(false);
      }
    },
    [isInitialized, permissions]
  );

  const triggerFetch = useCallback(async () => {
    if (Platform.OS !== 'android') {
      setError('Health Connect is Android-only');
      return;
    }

    const hasPerms = hasAllPermissions();
    if (!hasPerms) {
      const result = await requestPermissions();
      if (!result.success) return;
      await fetchData();
    } else {
      await fetchData();
    }
  }, [hasAllPermissions, requestPermissions, fetchData]);

  const revokeAccess = useCallback(() => {
    setPermissions([]);
    setData({
      sleep: 0,
      weight: 0,
      height: 0,
      distance: 0,
      steps: 0,
      stepsCadence: 0,
      totalCaloriesBurned: 0,
      calories: 0,
      oxygenSaturation: 0,
      heartRate: 0,
      restingHeartRate: 0,
    });
    setDailyDataArray([]);
    setSuccess(false);
    setError(null);
    setDataTimestamp(null);
    Alert.alert(
      'Access Revoked',
      'Permissions cleared locally. To fully revoke, open the Health Connect app and remove access for this app.',
      [
        {
          text: 'Go to Health Connect',
          onPress: async () => {
            try {
              await openHealthConnectSettings();
            } catch (err) {
              console.error('Failed to open Health Connect settings:', err);
            }
          },
        },
        { text: 'Ok', style: 'cancel' },
      ]
    );
  }, []);

  useEffect(() => {
    if (permissions.length > 0 && hasAllPermissions()) {
      fetchData();
    }
  }, [permissions]);

  return {
    // ✅ 화면 표시용 (최신 하루치)
    sleep: data.sleep,
    weight: data.weight,
    height: data.height,
    distance: data.distance,
    steps: data.steps,
    stepsCadence: data.stepsCadence,
    totalCaloriesBurned: data.totalCaloriesBurned,
    calories: data.calories,
    oxygenSaturation: data.oxygenSaturation,
    heartRate: data.heartRate,
    restingHeartRate: data.restingHeartRate,

    // ✅ 서버 전송용 (최근 1일치 배열)
    dailyDataArray,

    error,
    hasPermissions: hasAllPermissions(),
    success,
    dataTimestamp,
    onPress: triggerFetch,
    refetch: triggerFetch,
    revokeAccess,
  };
};

export default useHealthConnect;
