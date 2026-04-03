{/* Common labels */}
{{- define "ml-platform.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: ml-platform
{{- end }}
