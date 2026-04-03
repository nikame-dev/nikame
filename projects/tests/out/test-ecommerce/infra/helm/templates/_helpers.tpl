{/* Common labels */}
{{- define "ecommerce.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
nikame.project: ecommerce
{{- end }}
