{/* Common labels */}
{{- define "saas-starter.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: saas-starter
{{- end }}
