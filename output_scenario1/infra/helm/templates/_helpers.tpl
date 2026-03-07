{/* Common labels */}
{{- define "test-rag-scenario.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: test-rag-scenario
{{- end }}
