{/* Common labels */}
{{- define "rag-platform.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: rag-platform
{{- end }}
