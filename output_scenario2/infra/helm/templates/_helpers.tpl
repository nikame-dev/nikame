{/* Common labels */}
{{- define "test-event-scenario.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: test-event-scenario
{{- end }}
