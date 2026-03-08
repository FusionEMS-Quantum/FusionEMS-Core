FROM node:22-alpine3.22 AS deps

WORKDIR /app

RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json ./

RUN npm ci


FROM node:22-alpine3.22 AS builder

WORKDIR /app

RUN apk add --no-cache libc6-compat

ARG NEXT_PUBLIC_API_BASE
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_ROOT_DOMAIN
ARG NEXT_PUBLIC_BILLING_PHONE
ARG NEXT_PUBLIC_CNAM_DISPLAY_NAME

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NEXT_PUBLIC_ROOT_DOMAIN=$NEXT_PUBLIC_ROOT_DOMAIN
ENV NEXT_PUBLIC_BILLING_PHONE=$NEXT_PUBLIC_BILLING_PHONE
ENV NEXT_PUBLIC_CNAM_DISPLAY_NAME=$NEXT_PUBLIC_CNAM_DISPLAY_NAME

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build


FROM node:22-alpine3.22 AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0

RUN apk add --no-cache libc6-compat curl

RUN addgroup -S nextjs && adduser -S nextjs -G nextjs

# Next.js standalone output is not consistently generated across all builds.
# For reliability in production, run with `next start` and the built `.next` directory.
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.mjs ./next.config.mjs

RUN chown -R nextjs:nextjs /app

USER nextjs

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:3000/healthz || exit 1

CMD ["node_modules/.bin/next", "start", "-p", "3000", "-H", "0.0.0.0"]
