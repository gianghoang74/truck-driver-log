// Auto-generated sample payload for ?demo=1 preview (no API key needed).
export default {
  "inputs": {
    "current_location": "Dallas, TX",
    "pickup_location": "Oklahoma City, OK",
    "dropoff_location": "Denver, CO",
    "current_cycle_used_hrs": 8.0
  },
  "route": {
    "distance_mi": 970.0,
    "drive_hrs": 17.64,
    "geometry": {
      "type": "LineString",
      "coordinates": [
        [
          -96.797,
          32.7767
        ],
        [
          -97.13,
          33.63
        ],
        [
          -97.3,
          34.3
        ],
        [
          -97.44,
          35.22
        ],
        [
          -97.5164,
          35.4676
        ],
        [
          -98.7,
          35.52
        ],
        [
          -100.2,
          35.22
        ],
        [
          -101.83,
          35.22
        ],
        [
          -101.97,
          35.86
        ],
        [
          -102.98,
          36.5
        ],
        [
          -104.5,
          37.17
        ],
        [
          -104.61,
          38.25
        ],
        [
          -104.82,
          38.83
        ],
        [
          -104.94,
          39.3
        ],
        [
          -104.9903,
          39.7392
        ]
      ]
    },
    "waypoints": {
      "current": [
        -96.797,
        32.7767
      ],
      "pickup": [
        -97.5164,
        35.4676
      ],
      "dropoff": [
        -104.9903,
        39.7392
      ]
    }
  },
  "stops": [
    {
      "type": "pickup",
      "label": "Oklahoma City, OK",
      "arrive": "2026-07-16T09:49:05.454545",
      "duration_hrs": 1.0,
      "mile": 210.0,
      "coordinates": [
        -97.5164,
        35.4676
      ],
      "satisfies_break": true
    },
    {
      "type": "rest",
      "label": null,
      "arrive": "2026-07-16T18:00:00",
      "duration_hrs": 10.0,
      "mile": 605.0,
      "coordinates": [
        -102.47206130113005,
        36.17813785418142
      ],
      "satisfies_break": true
    },
    {
      "type": "dropoff",
      "label": "Denver, CO",
      "arrive": "2026-07-17T10:38:10.909091",
      "duration_hrs": 1.0,
      "mile": 970.0,
      "coordinates": [
        -104.9903,
        39.7392
      ],
      "satisfies_break": true
    }
  ],
  "days": [
    {
      "index": 1,
      "date": "2026-07-16",
      "total_miles": 605,
      "segments": [
        {
          "status": "off_duty",
          "start": "00:00",
          "end": "06:00",
          "location": null,
          "note": null
        },
        {
          "status": "driving",
          "start": "06:00",
          "end": "09:45",
          "location": "Dallas, TX",
          "note": "Start driving"
        },
        {
          "status": "on_duty",
          "start": "09:45",
          "end": "10:45",
          "location": "Oklahoma City, OK",
          "note": "Pickup"
        },
        {
          "status": "driving",
          "start": "10:45",
          "end": "18:00",
          "location": "Oklahoma City, OK",
          "note": "Start driving"
        },
        {
          "status": "sleeper",
          "start": "18:00",
          "end": "24:00",
          "location": null,
          "note": "10-hour rest"
        }
      ],
      "totals": {
        "off_duty": 6.0,
        "sleeper": 6.0,
        "driving": 11.0,
        "on_duty": 1.0
      },
      "total_hours": 24.0,
      "remarks": [
        {
          "time": "06:00",
          "location": "Dallas, TX",
          "note": "Start driving"
        },
        {
          "time": "09:49",
          "location": "Oklahoma City, OK",
          "note": "Pickup"
        },
        {
          "time": "10:49",
          "location": "Oklahoma City, OK",
          "note": "Start driving"
        },
        {
          "time": "18:00",
          "location": null,
          "note": "10-hour rest"
        }
      ],
      "recap": {
        "on_duty_today": 12.0,
        "used_last_8_days": 20.0,
        "available_tomorrow": 50.0
      }
    },
    {
      "index": 2,
      "date": "2026-07-17",
      "total_miles": 365,
      "segments": [
        {
          "status": "sleeper",
          "start": "00:00",
          "end": "04:00",
          "location": null,
          "note": "10-hour rest"
        },
        {
          "status": "driving",
          "start": "04:00",
          "end": "10:45",
          "location": null,
          "note": null
        },
        {
          "status": "on_duty",
          "start": "10:45",
          "end": "11:45",
          "location": "Denver, CO",
          "note": "Dropoff"
        },
        {
          "status": "off_duty",
          "start": "11:45",
          "end": "24:00",
          "location": null,
          "note": null
        }
      ],
      "totals": {
        "off_duty": 12.25,
        "sleeper": 4.0,
        "driving": 6.75,
        "on_duty": 1.0
      },
      "total_hours": 24.0,
      "remarks": [
        {
          "time": "10:38",
          "location": "Denver, CO",
          "note": "Dropoff"
        }
      ],
      "recap": {
        "on_duty_today": 7.75,
        "used_last_8_days": 27.75,
        "available_tomorrow": 42.25
      }
    }
  ],
  "id": "demo01"
};
