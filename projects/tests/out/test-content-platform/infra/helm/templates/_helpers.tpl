{/* Common labels */}
{{- define "content-platform.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: content-platform
{{- end }}
